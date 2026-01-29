import request from '@/utils/request';

const methods = {
  startAsr: {
    url: '/v1/file/asr/start',
    method: 'post',
  },
  getAsrStatus: {
    url: '/v1/file/asr/status',
    method: 'get',
  },
  getAsrPreview: {
    url: '/v1/file/asr/preview',
    method: 'get',
  },
} as const;

const fileAsrService = {
  startAsr: async (params: { file_id: string }) => {
    const response = await request.post(methods.startAsr.url, { data: params });
    return response;
  },
  getAsrStatus: async (params: { task_id: string }) => {
    const response = await request.get(methods.getAsrStatus.url, { params });
    return response;
  },
  getAsrPreview: async (params: { file_id: string }) => {
    const response = await request.get(methods.getAsrPreview.url, { params });
    return response;
  },
};

export default fileAsrService;
export { fileAsrService as FileAsrService };
