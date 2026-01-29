import { PromptIcon } from '@/assets/icon/next-icon';
import CopyToClipboard from '@/components/copy-to-clipboard';
import { useSetModalState } from '@/hooks/common-hooks';
import { IRemoveMessageById } from '@/hooks/logic-hooks';
import { api_host } from '@/utils/api';
import {
  DeleteOutlined,
  DislikeOutlined,
  DownloadOutlined,
  LikeOutlined,
  PauseCircleOutlined,
  SoundOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { Radio, Tooltip } from 'antd';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import FeedbackDialog from '../feedback-dialog';
import { PromptDialog } from '../prompt-dialog';
import { useRemoveMessage, useSendFeedback, useSpeech } from './hooks';
import { useTts } from './use-tts';

interface IProps {
  messageId: string;
  content: string;
  prompt?: string;
  showLikeButton: boolean;
  audioBinary?: string;
  showLoudspeaker?: boolean;
  conversationId?: string;
  ttsFileUrl?: string;
  ttsStatus?: string;
}

export const AssistantGroupButton = ({
  messageId,
  content,
  prompt,
  audioBinary,
  showLikeButton,
  showLoudspeaker = true,
  conversationId,
  ttsFileUrl,
  ttsStatus,
}: IProps) => {
  const { visible, hideModal, showModal, onFeedbackOk, loading } =
    useSendFeedback(messageId);
  const {
    visible: promptVisible,
    hideModal: hidePromptModal,
    showModal: showPromptModal,
  } = useSetModalState();
  const { t } = useTranslation();
  const { handleRead, ref, isPlaying } = useSpeech(
    content,
    audioBinary,
    ttsFileUrl,
    conversationId,
  );
  const { generateTts, isGenerating } = useTts();

  const handleLike = useCallback(() => {
    onFeedbackOk({ thumbup: true });
  }, [onFeedbackOk]);

  const handleGenerateTts = useCallback(async () => {
    if (conversationId) {
      await generateTts({ conversationId, content });
    }
  }, [conversationId, content, generateTts]);

  const handleDownloadTts = useCallback(() => {
    if (conversationId) {
      try {
        const link = document.createElement('a');
        link.href = `${api_host}/conversation/tts/down?conversation_id=${conversationId}`;
        link.download = `tts-${conversationId}.mp3`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } catch (error) {
        console.error('Download TTS failed:', error);
      }
    }
  }, [conversationId]);

  return (
    <>
      <Radio.Group size="small">
        <Radio.Button value="a">
          <CopyToClipboard text={content}></CopyToClipboard>
        </Radio.Button>
        {conversationId && (
          <Radio.Button
            value="e"
            onClick={handleGenerateTts}
            disabled={isGenerating}
          >
            <Tooltip title="合成语音">
              <SoundOutlined spin={isGenerating} />
            </Tooltip>
          </Radio.Button>
        )}
        {showLoudspeaker && (
          <Radio.Button value="b" onClick={handleRead} disabled={false}>
            <Tooltip title={t('chat.read')}>
              {isPlaying ? <PauseCircleOutlined /> : <SoundOutlined />}
            </Tooltip>
            <audio src="" ref={ref}>
              {' '}
            </audio>
          </Radio.Button>
        )}
        {conversationId && (
          <Radio.Button value="f" onClick={handleDownloadTts} disabled={false}>
            <Tooltip title="下载语音">
              <DownloadOutlined />
            </Tooltip>
          </Radio.Button>
        )}
        {showLikeButton && (
          <>
            <Radio.Button value="c" onClick={handleLike}>
              <LikeOutlined />
            </Radio.Button>
            <Radio.Button value="d" onClick={showModal}>
              <DislikeOutlined />
            </Radio.Button>
          </>
        )}
        {prompt && (
          <Radio.Button value="e" onClick={showPromptModal}>
            <PromptIcon style={{ fontSize: '16px' }} />
          </Radio.Button>
        )}
      </Radio.Group>
      {visible && (
        <FeedbackDialog
          visible={visible}
          hideModal={hideModal}
          onOk={onFeedbackOk}
          loading={loading}
        ></FeedbackDialog>
      )}
      {promptVisible && (
        <PromptDialog
          visible={promptVisible}
          hideModal={hidePromptModal}
          prompt={prompt}
        ></PromptDialog>
      )}
    </>
  );
};

interface UserGroupButtonProps extends Partial<IRemoveMessageById> {
  messageId: string;
  content: string;
  regenerateMessage?: () => void;
  sendLoading: boolean;
}

export const UserGroupButton = ({
  content,
  messageId,
  sendLoading,
  removeMessageById,
  regenerateMessage,
}: UserGroupButtonProps) => {
  const { onRemoveMessage, loading } = useRemoveMessage(
    messageId,
    removeMessageById,
  );
  const { t } = useTranslation();

  return (
    <Radio.Group size="small">
      <Radio.Button value="a">
        <CopyToClipboard text={content}></CopyToClipboard>
      </Radio.Button>
      {regenerateMessage && (
        <Radio.Button
          value="b"
          onClick={regenerateMessage}
          disabled={sendLoading}
        >
          <Tooltip title={t('chat.regenerate')}>
            <SyncOutlined spin={sendLoading} />
          </Tooltip>
        </Radio.Button>
      )}
      {removeMessageById && (
        <Radio.Button value="c" onClick={onRemoveMessage} disabled={loading}>
          <Tooltip title={t('common.delete')}>
            <DeleteOutlined spin={loading} />
          </Tooltip>
        </Radio.Button>
      )}
    </Radio.Group>
  );
};
