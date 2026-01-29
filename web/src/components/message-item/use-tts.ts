import { apiService } from '@/services/api-service';
import { message } from 'antd';
import { useCallback, useState } from 'react';

interface GenerateTtsParams {
  conversationId: string;
  content: string;
}

export const useTts = () => {
  const [isGenerating, setIsGenerating] = useState(false);

  const generateTts = useCallback(
    async ({ conversationId, content }: GenerateTtsParams) => {
      try {
        setIsGenerating(true);
        const response = await apiService.generateTts({
          conversation_id: conversationId,
          content,
        });
        if (response.code === 0) {
          message.success('合成语音请求已发送');
        } else {
          message.error(response.message || '合成语音失败');
        }
      } catch (error) {
        console.error('生成语音失败:', error);
        message.error('生成语音失败，请稍后重试');
      } finally {
        setIsGenerating(false);
      }
    },
    [],
  );

  return {
    generateTts,
    isGenerating,
  };
};
