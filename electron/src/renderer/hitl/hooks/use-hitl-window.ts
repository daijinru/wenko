import { useState, useEffect, useCallback } from 'react';
import type { HITLRequest, HITLField, HITLResultResponse } from '../types/hitl';
import { submitHITL, onHITLRequestData } from '../lib/ipc-client';

interface HITLWindowState {
  request: HITLRequest | null;
  sessionId: string | null;
  formData: Record<string, unknown>;
  error: string | null;
  isSubmitting: boolean;
  isLoaded: boolean;
}

export function useHITLWindow() {
  const [state, setState] = useState<HITLWindowState>({
    request: null,
    sessionId: null,
    formData: {},
    error: null,
    isSubmitting: false,
    isLoaded: false,
  });

  // Initialize form data with defaults
  const initializeFormData = useCallback((fields: HITLField[]) => {
    const initialData: Record<string, unknown> = {};
    fields.forEach((field) => {
      if (field.default !== undefined) {
        initialData[field.name] = field.default;
      } else if (field.type === 'checkbox' || field.type === 'multiselect') {
        initialData[field.name] = [];
      } else if (field.type === 'boolean') {
        initialData[field.name] = false;
      } else if (field.type === 'slider' || field.type === 'number') {
        initialData[field.name] = field.min ?? 0;
      }
    });
    return initialData;
  }, []);

  // Listen for request data from main process
  useEffect(() => {
    const unsubscribe = onHITLRequestData((data) => {
      console.log('[HITL Window] Received request data:', data);
      const initialFormData = initializeFormData(data.request.fields);
      setState({
        request: data.request,
        sessionId: data.sessionId,
        formData: initialFormData,
        error: null,
        isSubmitting: false,
        isLoaded: true,
      });
    });

    return unsubscribe;
  }, [initializeFormData]);

  // Update a field value
  const updateField = useCallback((fieldName: string, value: unknown) => {
    setState((prev) => ({
      ...prev,
      formData: {
        ...prev.formData,
        [fieldName]: value,
      },
      error: null,
    }));
  }, []);

  // Submit form (approve or reject)
  const submit = useCallback(async (action: 'approve' | 'reject') => {
    if (!state.request || !state.sessionId) {
      console.error('[HITL Window] No request data');
      return;
    }

    setState((prev) => ({ ...prev, isSubmitting: true, error: null }));

    const result = await submitHITL({
      requestId: state.request.id,
      sessionId: state.sessionId,
      action,
      formData: action === 'approve' ? state.formData : null,
    });

    if (!result.success && result.error) {
      setState((prev) => ({
        ...prev,
        isSubmitting: false,
        error: result.error ?? null,
      }));
    } else {
      setState((prev) => ({ ...prev, isSubmitting: false }));
      // Window will be closed by main process on success
    }
  }, [state.request, state.sessionId, state.formData]);

  return {
    request: state.request,
    formData: state.formData,
    error: state.error,
    isSubmitting: state.isSubmitting,
    isLoaded: state.isLoaded,
    updateField,
    submit,
  };
}
