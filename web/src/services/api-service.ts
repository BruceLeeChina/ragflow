import api from '@/utils/api';
import { http } from '@/utils/http';

interface GenerateTtsParams {
  conversation_id: string;
  content: string;
}

export const apiService = {
  generateTts: async (params: GenerateTtsParams) => {
    console.log('TTS params:', params);
    const response = await http.post(api.ttsGenerate, {
      conversation_id: params.conversation_id,
      content: params.content,
    });
    console.log('TTS response:', response);
    return response;
  },
};
