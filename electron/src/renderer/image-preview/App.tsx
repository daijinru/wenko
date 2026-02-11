import { useImagePreview } from './hooks/use-image-preview';
import './styles/globals.css';

export default function App() {
  const {
    imageData,
    isLoaded,
    isAnalyzing,
    analysisResult,
    error,
    analyze,
    cancel,
    saveToMemory,
  } = useImagePreview();

  if (!isLoaded) {
    return (
      <div className="theme-classic h-screen flex items-center justify-center">
        <span className="text-xs">loading...</span>
      </div>
    );
  }

  if (!imageData) {
    return (
      <div className="theme-classic h-screen flex items-center justify-center">
        <span className="text-xs text-muted-foreground">no data</span>
      </div>
    );
  }

  return (
    <div className="theme-classic h-screen flex flex-col">
      <div className="window active flex-1 flex flex-col">
        {/* Title bar */}
        <header className="window-draggable bg-classic-title border-b border-border !p-[6px] !mb-[6px] flex justify-between items-center">
          <h1 className="flex-1 text-center text-xs font-bold">Image Preview</h1>
        </header>

        {/* Content */}
        <div className="!p-[12px] window-body flex-1 flex flex-col overflow-hidden">
          {/* Image preview */}
          <div className="flex justify-center mb-4">
            <img
              src={imageData}
              alt="Preview"
              style={{
                maxWidth: '100%',
                maxHeight: '200px',
                borderRadius: '4px',
                objectFit: 'contain',
                border: '1px solid #ccc',
              }}
            />
          </div>

          {/* Analysis result */}
          {analysisResult?.extractedText && (
            <div className="flex-1 overflow-auto mb-4">
              <div className="text-xs font-bold mb-2">Extracted text:</div>
              <div
                className="p-2 bg-white border border-gray-300 rounded text-xs"
                style={{ whiteSpace: 'pre-wrap', maxHeight: '150px', overflow: 'auto' }}
              >
                {analysisResult.extractedText}
              </div>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="mb-4 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
              {error}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex justify-end gap-2 !pt-2 border-t border-gray-200">
            <button
              className="button"
              onClick={cancel}
              disabled={isAnalyzing}
            >
              Cancel
            </button>

            {!analysisResult ? (
              <button
                className="button default"
                onClick={analyze}
                disabled={isAnalyzing}
              >
                {isAnalyzing ? 'Analyzing...' : 'Analyze'}
              </button>
            ) : (
              <button
                className="button default"
                onClick={saveToMemory}
                disabled={isAnalyzing}
              >
                {isAnalyzing ? 'Saving...' : 'Save to Memory'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
