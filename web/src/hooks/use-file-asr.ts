import { FileAsrService } from '@/services/file-asr-service';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

export function useStartAsr() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: FileAsrService.startAsr,
    onSuccess: async () => {
      // Refresh file list to update ASR status
      queryClient.invalidateQueries({ queryKey: ['fetchFileList'] });
      // Invalidate any ASR status queries
      queryClient.invalidateQueries({ queryKey: ['asrStatus'] });
    },
    onError: (error) => {
      console.error('Error starting ASR:', error);
    },
  });

  return {
    startAsr: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}

export function useGetAsrStatus() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: FileAsrService.getAsrStatus,
    onError: (error) => {
      console.error('Error getting ASR status:', error);
    },
  });

  return {
    getAsrStatus: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}

export function useAsrStatus(taskId: string) {
  return useQuery({
    queryKey: ['asrStatus', taskId],
    queryFn: () => FileAsrService.getAsrStatus({ task_id: taskId }),
    enabled: !!taskId,
    refetchInterval: (data) => {
      if (data?.data?.status === 'processing') {
        return 3000; // Refresh every 3 seconds while processing
      }
      return false; // Stop refreshing when not processing
    },
  });
}

export function useGetAsrPreview() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: FileAsrService.getAsrPreview,
    onError: (error) => {
      console.error('Error getting ASR preview:', error);
    },
  });

  return {
    getAsrPreview: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}
