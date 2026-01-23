import { useState, useEffect, useCallback } from 'react';

interface ImagePreviewData {
  imageData: string;
  sessionId: string;
}

interface AnalysisResult {
  success: boolean;
  extractedText?: string;
  error?: string;
}

export function useImagePreview() {
  const [imageData, setImageData] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Listen for image data from main process
  useEffect(() => {
    if (!window.electronAPI?.on) return;

    const unsubscribe = window.electronAPI.on('image-preview:data', (data: ImagePreviewData) => {
      console.log('[ImagePreview] Received data');
      setImageData(data.imageData);
      setSessionId(data.sessionId);
      setIsLoaded(true);
    });

    return () => {
      unsubscribe?.();
    };
  }, []);

  // Analyze image
  const analyze = useCallback(async () => {
    if (!imageData || !sessionId || isAnalyzing) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const result = await window.electronAPI?.invoke('image-preview:analyze', {
        imageData,
        sessionId,
      });

      if (result.success) {
        setAnalysisResult(result);
      } else {
        setError(result.error || '分析失败');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '分析失败';
      setError(errorMessage);
    } finally {
      setIsAnalyzing(false);
    }
  }, [imageData, sessionId, isAnalyzing]);

  // Cancel and close window
  const cancel = useCallback(async () => {
    await window.electronAPI?.invoke('image-preview:cancel');
  }, []);

  // Save to memory (after analysis)
  const saveToMemory = useCallback(async () => {
    if (!analysisResult?.extractedText || !sessionId) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const result = await window.electronAPI?.invoke('image-preview:save-memory', {
        extractedText: analysisResult.extractedText,
        sessionId,
      });

      if (result.success) {
        // Close window after saving
        await window.electronAPI?.invoke('image-preview:close');
      } else {
        setError(result.error || '保存失败');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '保存失败';
      setError(errorMessage);
    } finally {
      setIsAnalyzing(false);
    }
  }, [analysisResult, sessionId]);

  return {
    imageData,
    isLoaded,
    isAnalyzing,
    analysisResult,
    error,
    analyze,
    cancel,
    saveToMemory,
  };
}
