import { useState, useEffect, useCallback } from 'react';
import type { ECSRequest, ECSField, AnyECSRequest } from '../types/ecs';
import { isDisplayRequest } from '../types/ecs';
import { submitECS, onECSRequestData } from '../lib/ipc-client';

interface ECSWindowState {
  request: AnyECSRequest | null;
  sessionId: string | null;
  formData: Record<string, unknown>;
  error: string | null;
  isSubmitting: boolean;
  isLoaded: boolean;
}

export function useECSWindow() {
  const [state, setState] = useState<ECSWindowState>({
    request: null,
    sessionId: null,
    formData: {},
    error: null,
    isSubmitting: false,
    isLoaded: false,
  });

  // Initialize form data with defaults
  const initializeFormData = useCallback((fields: ECSField[]) => {
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
    const unsubscribe = onECSRequestData((data) => {
      console.log('[ECS Window] Received request data:', data);
      // For visual display, no form data needed
      const initialFormData = isDisplayRequest(data.request)
        ? {}
        : initializeFormData((data.request as ECSRequest).fields);
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
      console.error('[ECS Window] No request data');
      return;
    }

    setState((prev) => ({ ...prev, isSubmitting: true, error: null }));

    const result = await submitECS({
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
