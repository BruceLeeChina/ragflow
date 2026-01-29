import { PromptIcon } from '@/assets/icon/next-icon';
import CopyToClipboard from '@/components/copy-to-clipboard';
import { useSetModalState } from '@/hooks/common-hooks';
import { IRemoveMessageById } from '@/hooks/logic-hooks';
import { AgentChatContext } from '@/pages/agent/context';
import { downloadFile } from '@/services/file-manager-service';
import { api_host } from '@/utils/api';
import { downloadFileFromBlob } from '@/utils/file-util';
import {
  DeleteOutlined,
  DislikeOutlined,
  LikeOutlined,
  PauseCircleOutlined,
  SoundOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { Radio, Tooltip } from 'antd';
import { Download, NotebookText } from 'lucide-react';
import { useCallback, useContext } from 'react';
import { useTranslation } from 'react-i18next';
import FeedbackDialog from '../feedback-dialog';
import { useTts } from '../message-item/use-tts';
import { PromptDialog } from '../prompt-dialog';
import { ToggleGroup, ToggleGroupItem } from '../ui/toggle-group';
import { useRemoveMessage, useSendFeedback, useSpeech } from './hooks';

interface IProps {
  messageId: string;
  content: string;
  prompt?: string;
  showLikeButton: boolean;
  audioBinary?: string;
  showLoudspeaker?: boolean;
  showLog?: boolean;
  conversationId?: string;
  ttsFileUrl?: string;
  ttsStatus?: string;
  attachment?: {
    file_name: string;
    doc_id: string;
    format: string;
  };
}

export const AssistantGroupButton = ({
  messageId,
  content,
  prompt,
  audioBinary,
  showLikeButton,
  showLoudspeaker = true,
  showLog = true,
  conversationId,
  ttsFileUrl,
  ttsStatus,
  attachment,
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

  const { showLogSheet } = useContext(AgentChatContext);

  const handleShowLogSheet = useCallback(() => {
    showLogSheet(messageId);
  }, [messageId, showLogSheet]);

  return (
    <>
      <ToggleGroup
        type={'single'}
        size="sm"
        variant="outline"
        className="space-x-1"
      >
        <ToggleGroupItem value="a">
          <CopyToClipboard text={content}></CopyToClipboard>
        </ToggleGroupItem>
        {conversationId && (
          <ToggleGroupItem
            value="e"
            onClick={handleGenerateTts}
            disabled={isGenerating}
          >
            <Tooltip title="合成语音">
              <SoundOutlined spin={isGenerating} />
            </Tooltip>
          </ToggleGroupItem>
        )}
        {showLoudspeaker && (
          <ToggleGroupItem value="b" onClick={handleRead} disabled={false}>
            <Tooltip title={t('chat.read')}>
              {isPlaying ? <PauseCircleOutlined /> : <SoundOutlined />}
            </Tooltip>
            <audio src="" ref={ref}>
              {' '}
            </audio>
          </ToggleGroupItem>
        )}
        {conversationId && (
          <ToggleGroupItem
            value="g"
            onClick={handleDownloadTts}
            disabled={false}
          >
            <Tooltip title="下载语音">
              <Download size={16} />
            </Tooltip>
          </ToggleGroupItem>
        )}
        {showLikeButton && (
          <>
            <ToggleGroupItem value="c" onClick={handleLike}>
              <LikeOutlined />
            </ToggleGroupItem>
            <ToggleGroupItem value="d" onClick={showModal}>
              <DislikeOutlined />
            </ToggleGroupItem>
          </>
        )}
        {prompt && (
          <Radio.Button value="e" onClick={showPromptModal}>
            <PromptIcon style={{ fontSize: '16px' }} />
          </Radio.Button>
        )}
        {showLog && (
          <ToggleGroupItem value="f" onClick={handleShowLogSheet}>
            <NotebookText className="size-4" />
          </ToggleGroupItem>
        )}
        {!!attachment?.doc_id && (
          <ToggleGroupItem
            value="g"
            onClick={async () => {
              try {
                const response = await downloadFile({
                  docId: attachment.doc_id,
                  ext: attachment.format,
                });
                const blob = new Blob([response.data], {
                  type: response.data.type,
                });
                downloadFileFromBlob(blob, attachment.file_name);
              } catch (error) {
                console.error('Download failed:', error);
              }
            }}
          >
            <Download size={16} />
          </ToggleGroupItem>
        )}
      </ToggleGroup>
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
