import { IconFontFill } from '@/components/icon-font';
import { Progress } from '@/components/ui/progress';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  useGetAsrPreview,
  useGetAsrStatus,
  useStartAsr,
} from '@/hooks/use-file-asr';
import { useDownloadFile } from '@/hooks/use-file-request';
import { IFile } from '@/interfaces/database/file-manager';
import { FileText, Pause, Play } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';

const IconMap = {
  pending: <IconFontFill name="play" className="text-accent-primary" />,
  processing: <IconFontFill name="reparse" className="text-accent-primary" />,
  completed: <IconFontFill name="reparse" className="text-accent-primary" />,
  failed: <IconFontFill name="reparse" className="text-accent-primary" />,
};

export function AsrStatusCell({ row }: { row: any }) {
  const { t } = useTranslation();
  const file = row.original as IFile;
  const { asr_status = 'pending', asr_progress = 0, asr_task_id } = file;
  const { startAsr, isLoading: isStartingAsr } = useStartAsr();
  const { getAsrStatus, isLoading: isGettingStatus } = useGetAsrStatus();
  const { getAsrPreview } = useGetAsrPreview();
  const { downloadFile } = useDownloadFile();

  const [isPlaying, setIsPlaying] = useState(false);
  const [audio, setAudio] = useState<HTMLAudioElement | null>(null);
  const [showAsrResult, setShowAsrResult] = useState(false);
  const [asrResult, setAsrResult] = useState('');

  const handleStartAsr = useCallback(async () => {
    try {
      await startAsr({ file_id: file.id });
      // Refresh file list or status after starting ASR
    } catch (error) {
      console.error('Error starting ASR:', error);
    }
  }, [file.id, startAsr]);

  const handleGetAsrStatus = useCallback(async () => {
    if (!asr_task_id) return;

    try {
      const status = await getAsrStatus({ task_id: asr_task_id });
      if (status.data.status === 'completed') {
        setAsrResult(status.data.result || '');
      }
    } catch (error) {
      console.error('Error getting ASR status:', error);
    }
  }, [asr_task_id, getAsrStatus]);

  const handlePlayAudio = useCallback(async () => {
    try {
      const audioUrl = `/v1/file/get/${file.id}`;
      const newAudio = new Audio(audioUrl);

      newAudio.onended = () => {
        setIsPlaying(false);
      };

      if (isPlaying && audio) {
        audio.pause();
        audio.currentTime = 0;
        setIsPlaying(false);
        setAudio(null);
      } else {
        await newAudio.play();
        setIsPlaying(true);
        setAudio(newAudio);
      }
    } catch (error) {
      console.error('Error playing audio:', error);
    }
  }, [file.id, isPlaying, audio]);

  const handleShowAsrResult = useCallback(async () => {
    if (asr_status === 'completed') {
      try {
        const previewResult = await getAsrPreview({ file_id: file.id });
        if (previewResult.data && typeof previewResult.data === 'object') {
          // Check if the result has a text field (new format)
          if (previewResult.data.text) {
            setAsrResult(previewResult.data.text);
          } else {
            // Fallback to old format
            setAsrResult(JSON.stringify(previewResult.data));
          }
        }
      } catch (error) {
        console.error('Error getting ASR preview:', error);
      }
      setShowAsrResult(true);
    }
  }, [asr_status, getAsrPreview, file.id]);

  const isAudioFile =
    file.type.includes('audio') ||
    file.name.match(/\.(mp3|wav|ogg|aac|flac)$/i);
  const p = Math.min(100, Math.max(0, asr_progress));

  return (
    <section className="flex flex-col gap-2 items-start">
      {isAudioFile && (
        <>
          {/* Play Audio Button */}
          <div className="flex gap-4 items-center">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={handlePlayAudio}
                  className="p-1 rounded-full hover:bg-bg-card transition-colors"
                  aria-label={isPlaying ? '暂停' : '播放'}
                >
                  {isPlaying ? <Pause size={16} /> : <Play size={16} />}
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{isPlaying ? '暂停' : '播放'}</p>
              </TooltipContent>
            </Tooltip>

            {/* ASR Status and Controls */}
            <div className="flex items-center gap-3">
              {asr_status === 'processing' ? (
                <>
                  <div className="flex items-center gap-1">
                    <Progress value={p} className="h-1 flex-1 min-w-20" />
                    {p}%
                  </div>
                </>
              ) : (
                <>
                  {asr_status === 'completed' && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          onClick={handleShowAsrResult}
                          className="p-1 rounded-full hover:bg-bg-card transition-colors"
                          aria-label="查看识别结果"
                        >
                          <FileText size={16} className="text-accent-primary" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>查看识别结果</p>
                      </TooltipContent>
                    </Tooltip>
                  )}

                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={handleStartAsr}
                        disabled={isStartingAsr || asr_status === 'processing'}
                        className="p-1 rounded-full hover:bg-bg-card transition-colors"
                        aria-label="语音识别"
                      >
                        {IconMap[asr_status as keyof typeof IconMap] ||
                          IconMap.pending}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>语音识别</p>
                    </TooltipContent>
                  </Tooltip>
                </>
              )}
            </div>
          </div>

          {/* ASR Status Text */}
          <div className="ml-8 text-sm">
            {asr_status === 'pending' && (
              <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded">
                待识别
              </span>
            )}
            {asr_status === 'processing' && (
              <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded">
                识别中
              </span>
            )}
            {asr_status === 'completed' && (
              <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded">
                已完成
              </span>
            )}
            {asr_status === 'failed' && (
              <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded">
                识别失败
              </span>
            )}
          </div>

          {/* ASR Result Preview */}
          {asr_status === 'completed' && asrResult && (
            <div className="ml-8 mt-1 text-xs text-gray-600 max-w-xs truncate">
              识别结果：{asrResult}
            </div>
          )}

          {/* ASR Result Modal */}
          {showAsrResult && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-card p-6 rounded-lg max-w-md w-full max-h-[80vh] overflow-auto">
                <h3 className="text-lg font-semibold mb-4">识别结果</h3>
                <div className="prose">
                  <p>{asrResult || '无识别结果'}</p>
                </div>
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={() => setShowAsrResult(false)}
                    className="px-4 py-2 bg-accent-primary text-white rounded hover:bg-accent-primary/90 transition-colors"
                  >
                    关闭
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
