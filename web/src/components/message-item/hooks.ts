import { useSetModalState } from '@/hooks/common-hooks';
import { IRemoveMessageById, useSpeechWithSse } from '@/hooks/logic-hooks';
import { useDeleteMessage, useFeedback } from '@/hooks/use-chat-request';
import { IFeedbackRequestBody } from '@/interfaces/request/chat';
import { hexStringToUint8Array } from '@/utils/common-util';
import { SpeechPlayer } from 'openai-speech-stream-player';
import { useCallback, useEffect, useRef, useState } from 'react';

export const useSendFeedback = (messageId: string) => {
  const { visible, hideModal, showModal } = useSetModalState();
  const { feedback, loading } = useFeedback();

  const onFeedbackOk = useCallback(
    async (params: IFeedbackRequestBody) => {
      const ret = await feedback({
        ...params,
        messageId: messageId,
      });

      if (ret === 0) {
        hideModal();
      }
    },
    [feedback, hideModal, messageId],
  );

  return {
    loading,
    onFeedbackOk,
    visible,
    hideModal,
    showModal,
  };
};

export const useRemoveMessage = (
  messageId: string,
  removeMessageById?: IRemoveMessageById['removeMessageById'],
) => {
  const { deleteMessage, loading } = useDeleteMessage();

  const onRemoveMessage = useCallback(async () => {
    if (messageId) {
      const code = await deleteMessage(messageId);
      if (code === 0) {
        removeMessageById?.(messageId);
      }
    }
  }, [deleteMessage, messageId, removeMessageById]);

  return { onRemoveMessage, loading };
};

export const useSpeech = (
  content: string,
  audioBinary?: string,
  ttsFileUrl?: string,
) => {
  const ref = useRef<HTMLAudioElement>(null);
  const { read } = useSpeechWithSse();
  const player = useRef<SpeechPlayer>();
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  const initialize = useCallback(async () => {
    player.current = new SpeechPlayer({
      audio: ref.current!,
      onPlaying: () => {
        setIsPlaying(true);
      },
      onPause: () => {
        setIsPlaying(false);
      },
      onChunkEnd: () => {},
      mimeType: MediaSource.isTypeSupported('audio/mpeg')
        ? 'audio/mpeg'
        : 'audio/mp4; codecs="mp4a.40.2"', // https://stackoverflow.com/questions/64079424/cannot-replay-mp3-in-firefox-using-mediasource-even-though-it-works-in-chrome
    });
    await player.current.init();
  }, []);

  const pause = useCallback(() => {
    player.current?.pause();
  }, []);

  const speech = useCallback(async () => {
    if (ttsFileUrl) {
      // 如果有TTS文件URL，直接播放
      if (ref.current) {
        ref.current.src = ttsFileUrl;
        ref.current.play().catch((error) => {
          console.error('Error playing audio:', error);
          setIsPlaying(false);
        });
      }
    } else {
      // 否则使用语音合成
      const response = await read({ text: content });
      if (response) {
        player?.current?.feedWithResponse(response);
      }
    }
  }, [read, content, ttsFileUrl]);

  const handleRead = useCallback(async () => {
    if (isPlaying) {
      setIsPlaying(false);
      pause();
    } else {
      setIsPlaying(true);
      speech();
    }
  }, [setIsPlaying, speech, isPlaying, pause]);

  useEffect(() => {
    if (audioBinary) {
      const units = hexStringToUint8Array(audioBinary);
      if (units) {
        try {
          player.current?.feed(units);
        } catch (error) {
          console.warn(error);
        }
      }
    }
  }, [audioBinary]);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return { ref, handleRead, isPlaying };
};
