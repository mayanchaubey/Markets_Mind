import { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BrainCircuit,
  Send,
  Activity,
  TrendingUp,
  ShieldCheck,
  User,
  ExternalLink,
  Sparkles,
  ChevronRight,
  RotateCcw,
  Copy,
  Check,
  BookOpen,
  Zap,
  MessageSquare,
  AlertTriangle,
  Paperclip,
  X,
  FileText,
  Image as ImageIcon,
  File as FileIcon,
  Download,
} from 'lucide-react';
import { suggestionGroups, demoCannedResponses, demoChatResponse } from '../data/demoResponses';
import { IntelligencePanel } from '../components/IntelligencePanel';
import { api } from '../services/api';
import { useChat } from '../context/ChatContext';
import logo from '../assets/logo.png';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const UPLOAD_URL_ENDPOINT = `${API_BASE_URL}/upload-url`;
const CHAT_API_URL = import.meta.env.VITE_CHAT_ENDPOINT || 'http://localhost:8000/api/chat';


const ICON_MAP = { Activity, TrendingUp, ShieldCheck };

const getTimeAgo = (timestamp) => {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 60) return 'Just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};

const formatTime = (date) => {
  const d = typeof date === 'number' ? new Date(date) : date;
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
};

/* ─────────────────────────────────────────────────────────
   TYPING INDICATOR
───────────────────────────────────────────────────────── */
const TypingIndicator = () => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: 6 }}
    transition={{ duration: 0.3 }}
    className="flex items-end gap-3"
  >
    <div className="shrink-0 w-8 h-8 rounded-lg bg-white border border-border flex items-center justify-center shadow-sm">
      <BrainCircuit className="w-4 h-4 text-accent-primary" />
    </div>
    <div className="flex items-center gap-1.5 px-4 py-3 rounded-2xl rounded-bl-sm bg-white border border-border shadow-sm">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="block w-1.5 h-1.5 rounded-full bg-accent-primary"
          animate={{ y: [0, -5, 0], opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.18, ease: 'easeInOut' }}
        />
      ))}
    </div>
  </motion.div>
);

/* ─────────────────────────────────────────────────────────
   COPY BUTTON
───────────────────────────────────────────────────────── */
const CopyBtn = ({ text }) => {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="p-1.5 rounded-md text-text-secondary hover:text-text-primary hover:bg-accent-primary/10 transition-colors duration-200"
      title="Copy"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-success-green" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
};

/* ─────────────────────────────────────────────────────────
   MESSAGE BUBBLE
───────────────────────────────────────────────────────── */
const MessageBubble = ({ msg, index }) => {
  const isUser = msg.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.04, ease: [0.22, 1, 0.36, 1] }}
      className={`flex items-end gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {isUser ? (
        <div className="shrink-0 w-8 h-8 rounded-lg bg-[#FDECEC] border border-[#FAD4D0] flex items-center justify-center">
          <User className="w-4 h-4 text-accent-primary" />
        </div>
      ) : (
        <div className="shrink-0 w-8 h-8 rounded-lg bg-white border border-border flex items-center justify-center shadow-sm">
          <img src={logo} alt="MarketMind AI" className="w-6 h-6 object-contain" />
        </div>
      )}

      <div className={`group max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        {isUser ? (
          <div className="flex flex-col items-end gap-1">
            <div className={`px-4 py-3 rounded-2xl rounded-br-sm ${msg.status === 'error' ? 'bg-danger-red/10 border border-danger-red/40 text-danger-red shadow-sm' : 'bg-[#FDECEC] border border-[#FAD4D0] text-text-primary shadow-sm'} text-sm leading-relaxed font-medium`}>
              {msg.content}
              {/* Attachments Display */}
              {msg.attachments && msg.attachments.length > 0 && (
                <div className="mt-3 space-y-2">
                  {msg.attachments.map((file, i) => {
                    const isImg = file.mimeType?.startsWith('image/');
                    return (
                      <div
                        key={i}
                        className={`flex items-center gap-3 px-3 py-2 rounded-xl border ${msg.status === 'error' ? 'bg-danger-red/10 border-danger-red/40 text-danger-red' : 'bg-white border-border text-text-secondary shadow-sm'}`}
                      >
                        <div className="w-10 h-10 rounded-lg border border-border bg-white flex items-center justify-center overflow-hidden shrink-0">
                          {isImg ? (
                            <img src={file.url} alt={file.name} className="w-full h-full object-cover" />
                          ) : (
                            <FileText className="w-5 h-5 text-accent-primary" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0 pr-2">
                          <p className="text-[11px] font-semibold truncate text-text-primary">{file.name}</p>
                          <p className="text-[9px] text-text-secondary">{file.mimeType?.split('/')[1] || 'file'}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            {msg.status === 'error' && (
              <span className="flex items-center gap-1 text-[10px] font-semibold text-danger-red mt-1">
                <AlertTriangle className="w-3 h-3" />
                Message failed to send.
              </span>
            )}
          </div>
        ) : (
          <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-white border border-border shadow-sm text-sm leading-relaxed text-text-primary">
            {(() => {
              const lines = msg.content.split('\n');
              return lines.map((line, i) => {
                const trimmed = line.trim();

                if (!trimmed) return <div key={i} className="h-2" />;

                const renderInline = (text) =>
                  text.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
                    part.startsWith('**') && part.endsWith('**') ? (
                      <strong key={j} className="font-semibold text-text-primary">{part.slice(2, -2)}</strong>
                    ) : (
                      <span key={j}>{part}</span>
                    )
                  );

                if (/^[\*\+\-•]\s/.test(trimmed)) {
                  return (
                    <div key={i} className="flex items-start gap-2 my-0.5">
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent-primary shrink-0" />
                      <span className="text-sm leading-relaxed">{renderInline(trimmed.replace(/^[\*\+\-•]\s/, ''))}</span>
                    </div>
                  );
                }

                if (/^\t[\*\+\-]\s/.test(line) || /^  +[\*\+\-]\s/.test(line)) {
                  return (
                    <div key={i} className="flex items-start gap-2 my-0.5 ml-5">
                      <span className="mt-1.5 w-1 h-1 rounded-full bg-text-muted shrink-0" />
                      <span className="text-sm leading-relaxed text-text-secondary">{renderInline(trimmed.replace(/^[\*\+\-]\s/, ''))}</span>
                    </div>
                  );
                }

                return (
                  <p key={i} className="text-sm leading-relaxed my-0.5">
                    {renderInline(trimmed)}
                  </p>
                );
              });
            })()}

            {msg.attachments && msg.attachments.length > 0 && (
              <div className="mt-3 space-y-2">
                {msg.attachments.map((file, i) => {
                  const isImg = file.mimeType?.startsWith('image/');
                  return (
                    <div
                      key={i}
                      className="flex items-center gap-3 px-3 py-2 rounded-xl border border-border bg-white text-text-secondary shadow-sm"
                    >
                      <div className="w-10 h-10 rounded-lg border border-border bg-white flex items-center justify-center overflow-hidden shrink-0">
                        {isImg ? (
                          <img src={file.url} alt={file.name} className="w-full h-full object-cover" />
                        ) : (
                          <FileText className="w-5 h-5 text-accent-primary" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0 pr-2">
                        <p className="text-[11px] font-semibold truncate text-text-primary">{file.name}</p>
                        <p className="text-[9px] text-text-secondary">{file.mimeType?.split('/')[1] || 'file'}</p>
                      </div>
                      <a
                        href={file.url}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 rounded-lg text-text-secondary hover:text-accent-primary transition-colors"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                    </div>
                  );
                })}
              </div>
            )}

            {msg.sources && msg.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border flex flex-wrap gap-2">
                {msg.sources.map((src, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 text-[10px] font-semibold text-text-secondary px-2 py-0.5 rounded-full border border-border bg-white"
                  >
                    <BookOpen className="w-2.5 h-2.5" />
                    {src}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        <div className={`flex items-center gap-1.5 ${isUser ? 'flex-row-reverse' : 'flex-row'} opacity-0 group-hover:opacity-100 transition-opacity duration-200`}>
          <span className="text-[10px] text-text-muted font-mono">{formatTime(msg.timestamp)}</span>
          {!isUser && <CopyBtn text={msg.content} />}
        </div>
      </div>
    </motion.div>
  );
};

/* ─────────────────────────────────────────────────────────
   EMPTY STATE
───────────────────────────────────────────────────────── */
const EmptyState = ({ onSuggest }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.96 }}
    animate={{ opacity: 1, scale: 1 }}
    exit={{ opacity: 0, scale: 0.98 }}
    transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    className="flex flex-col items-center justify-center h-full text-center px-6 py-10 space-y-4 max-w-[320px] w-full mx-auto"
  >
    <div className="relative mb-6">

    </div>

    <h3 className="text-lg font-bold text-text-primary mb-2">MarketMind AI Terminal</h3>
    <p className="text-sm text-text-muted max-w-xs leading-relaxed">
      Ask anything about Indian markets — stock analysis, SEBI circulars, live signals, or macroeconomic trends.
    </p>

    <div className="mt-4 flex flex-wrap gap-2 justify-center w-full">
      {['NIFTY outlook today?', 'Analyse Reliance', 'Latest SEBI circular', 'Bearish signals now'].map((q) => (
        <button
          key={q}
          onClick={() => onSuggest(q)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border bg-white text-xs font-semibold text-text-secondary hover:border-accent-primary hover:text-text-primary transition-colors duration-200"
        >
          <Zap className="w-3 h-3" />
          {q}
        </button>
      ))}
    </div>
  </motion.div>
);

/* ─────────────────────────────────────────────────────────
   SIDEBAR (HISTORY & SUGGESTIONS)
───────────────────────────────────────────────────────── */
const ChatHistorySidebar = ({ onSuggest, isOpen, onClose }) => {
  const { chats, activeChatId, createChat, deleteChat, switchChat } = useChat();

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          />
        )}
      </AnimatePresence>

      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-72 lg:static flex flex-col shrink-0 border-r border-border bg-background-secondary transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        <div className="flex items-center justify-between px-5 py-5 border-b border-border bg-background-primary/20">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-interactive-primary" />
            <span className="text-xs font-bold text-text-primary uppercase tracking-widest">History</span>
          </div>
          <button
            onClick={() => { createChat(); if (window.innerWidth < 1024) onClose(); }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-interactive-primary text-white text-[11px] font-bold hover:bg-interactive-primary/90 transition-all font-mono"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            NEW
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6 scrollbar-hide">
          {chats.length > 0 && (
            <div className="space-y-1">
              <p className="px-2 mb-2 text-[9px] font-mono font-black uppercase tracking-[0.2em] text-text-muted opacity-50">Recent Logs</p>
              {chats.map((chat) => (
                <div key={chat.id} className="group relative">
                  <button
                    onClick={() => { switchChat(chat.id); if (window.innerWidth < 1024) onClose(); }}
                    className={`
                      w-full flex flex-col items-start gap-1 px-3 py-2.5 rounded-xl text-left transition-all duration-200 border
                      ${activeChatId === chat.id
                        ? 'bg-interactive-primary/10 border-interactive-primary/30 text-interactive-primary'
                        : 'bg-transparent border-transparent text-text-secondary hover:bg-background-card hover:border-border hover:text-text-primary'}
                    `}
                  >
                    <span className="text-xs font-semibold truncate w-full pr-8">{chat.title}</span>
                    <span className="text-[9px] font-mono opacity-60 uppercase">{getTimeAgo(chat.updated_at)}</span>
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteChat(chat.id); }}
                    className="absolute top-1/2 -translate-y-1/2 right-2 p-1.5 rounded-md text-text-muted opacity-0 group-hover:opacity-100 hover:text-danger-red hover:bg-danger-red/10 transition-all"
                  >
                    <AlertTriangle className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="pt-2 border-t border-border/50">
            {suggestionGroups.map((group) => {
              const Icon = ICON_MAP[group.icon] || Activity;
              return (
                <div key={group.label} className="mt-5 first:mt-2">
                  <div className="flex items-center gap-1.5 mb-2 px-1 text-text-muted">
                    <Icon className="w-3.5 h-3.5" />
                    <span className="text-[10px] font-bold uppercase tracking-widest">{group.label}</span>
                  </div>
                  <div className="space-y-1">
                    {group.items.map((item) => (
                      <button
                        key={item}
                        onClick={() => { onSuggest(item); if (window.innerWidth < 1024) onClose(); }}
                        className="group w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-left text-xs text-text-muted hover:text-text-primary hover:bg-background-card border border-transparent transition-all"
                      >
                        <span className="leading-snug line-clamp-2">{item}</span>
                        <ChevronRight className="w-3 h-3 shrink-0 opacity-0 group-hover:opacity-100" />
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </aside>
    </>
  );
};

/* ─────────────────────────────────────────────────────────
   MAIN CHAT PAGE
───────────────────────────────────────────────────────── */
export const ChatPage = () => {
  const location = useLocation();
  const { activeChat, activeChatId, addMessage, updateMessage, createChat, clearCurrentChat } = useChat();

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeQuery, setActiveQuery] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  const messages = activeChat?.messages || [];

  useEffect(() => {
    if (location.state?.query && messages.length === 0) {
      sendMessage(location.state.query);
    }
  }, [location.state]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  /* File select handler */
  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      const uploadPromises = files.map(async (file) => {
        const response = await fetch(UPLOAD_URL_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fileName: file.name,
            fileType: file.type || 'application/octet-stream',
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || 'Unable to initiate upload');
        }

        const { uploadUrl, fileUrl } = await response.json();
        if (!uploadUrl || !fileUrl) {
          throw new Error('Invalid upload URL response');
        }

        const putResponse = await fetch(uploadUrl, {
          method: 'PUT',
          headers: {
            'Content-Type': file.type || 'application/octet-stream',
          },
          body: file,
        });

        if (!putResponse.ok) {
          throw new Error('File upload failed');
        }

        return {
          url: fileUrl,
          name: file.name,
          mimeType: file.type,
          size: file.size,
        };
      });

      const uploadedResults = await Promise.all(uploadPromises);
      setSelectedFiles((prev) => [...prev, ...uploadedResults]);
    } catch (err) {
      console.error(err);
      setUploadError('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  /* Simulate AI response */
  const sendMessage = useCallback(
    async (query) => {
      const trimmedQuery = query.trim();
      if ((!trimmedQuery && selectedFiles.length === 0) || isTyping || isUploading) return;

      let currentChatId = activeChatId;

      if (!currentChatId) {
        currentChatId = createChat(trimmedQuery || 'File Analysis');
      }

      const userMsgId = Date.now().toString();
      const userMsg = {
        id: userMsgId,
        role: 'user',
        content: trimmedQuery,
        timestamp: Date.now(),
        type: selectedFiles.length > 0 ? 'mixed' : 'text',
        status: 'sending',
        attachments: [...selectedFiles],
      };

      addMessage(currentChatId, userMsg);
      setInput('');
      setSelectedFiles([]); // Clear pending files
      setActiveQuery(trimmedQuery);
      setIsTyping(true);
      inputRef.current?.focus();

      try {
        const response = await fetch(CHAT_API_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: trimmedQuery,
            history: [],
            attachments: [],
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || `Chat API error ${response.status}`);
        }

        const data = await response.json();
        console.log('Chat response intelligence:', data.intelligence || null);

        updateMessage(currentChatId, userMsgId, { status: 'done' });

        const aiMsg = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.answer || '',
          sources: data.sources || [],
          confidence: data.confidence || null,
          intent: data.intent || null,
          intelligence: data.intelligence || null,
          status: 'done',
          timestamp: Date.now(),
          type: 'text',
          attachments: [],
        };

        addMessage(currentChatId, aiMsg);

        if (data.intelligence) {
          setActiveQuery(trimmedQuery);
        }
      } catch (err) {
        console.error(err);
        updateMessage(currentChatId, userMsgId, { status: 'error' });
      } finally {
        setIsTyping(false);
      }
    },
    [isTyping, isUploading, selectedFiles, activeChatId, createChat, addMessage, updateMessage]
  );

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleSuggest = (text) => {
    setInput(text);
    sendMessage(text);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] -my-6 -mx-4 sm:-mx-6 lg:-mx-8 overflow-hidden relative">
      <ChatHistorySidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onSuggest={handleSuggest}
      />

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden bg-white border-l border-border">
        <div className="shrink-0 flex items-center justify-between px-5 py-3.5 border-b border-border bg-white z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="lg:hidden p-2 -ml-1 rounded-lg text-text-secondary hover:text-accent-primary"
            >
              <MessageSquare className="w-5 h-5 text-accent-primary" />
            </button>
            <div className="w-8 h-8 rounded-lg bg-white border border-accent-primary/40 flex items-center justify-center">
              <img src={logo} alt="MarketMind AI" className="w-6 h-6 object-contain" />
            </div>
            <div>
              <p className="text-sm font-bold text-text-primary leading-none truncate max-w-[140px] sm:max-w-xs">{activeChat?.title || 'MarketMind AI'}</p>
              <p className="text-[10px] text-text-muted font-mono mt-1 flex items-center gap-1.5">
                <motion.span
                  className="w-1.5 h-1.5 rounded-full bg-accent-primary"
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
                {isTyping ? 'Neural Agent Processing…' : 'Market Stream Active'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {activeChatId && (
              <button
                onClick={clearCurrentChat}
                className="p-2 rounded-lg text-text-muted hover:text-accent-primary hover:bg-accent-primary/10 transition-colors"
                title="Clear current chart"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            )}
            <div className="hidden sm:flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest text-text-muted border border-border rounded-lg px-2.5 py-1.5">
              <Zap className="w-3 h-3 text-warning-amber" />
              L4 INFRA
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-5">
          <AnimatePresence mode="wait">
            {messages.length === 0 && !isTyping ? (
              <EmptyState key="empty" onSuggest={handleSuggest} />
            ) : (
              <motion.div
                key="chat-flow"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-6"
              >
                {messages.map((msg, i) => (
                  <MessageBubble key={msg.id} msg={msg} index={i} />
                ))}
                {isTyping && <TypingIndicator />}
              </motion.div>
            )}
          </AnimatePresence>
          <div ref={bottomRef} className="h-4" />
        </div>

        <div className="shrink-0 border-t border-border bg-background-primary/80 backdrop-blur-xl px-4 sm:px-6 py-4">

          {/* File Upload Preview */}
          <AnimatePresence>
            {selectedFiles.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="flex flex-wrap gap-2 mb-3"
              >
                {selectedFiles.map((file, i) => (
                  <div key={i} className="group relative flex items-center gap-2 px-3 py-1.5 rounded-xl border border-border bg-background-card pr-8">
                    <div className="w-5 h-5 rounded flex items-center justify-center bg-interactive-primary/10">
                      {file.mimeType.startsWith('image/') ? <ImageIcon className="w-3 h-3 text-interactive-primary" /> : <FileText className="w-3 h-3 text-interactive-primary" />}
                    </div>
                    <span className="text-[11px] font-bold text-text-primary truncate max-w-[120px]">{file.name}</span>
                    <button
                      onClick={() => removeFile(i)}
                      className="absolute top-1/2 -translate-y-1/2 right-1.5 p-1 rounded-md text-text-muted hover:text-white hover:bg-white/10 transition-all opacity-0 group-hover:opacity-100"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Upload Status */}
          {isUploading && (
            <div className="flex items-center gap-2 mb-3 px-1 text-text-muted">
              <motion.div
                className="w-3 h-3 border-2 border-interactive-primary/20 border-t-interactive-primary rounded-full"
                animate={{ rotate: 360 }}
                transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
              />
              <span className="text-[10px] font-mono tracking-widest uppercase opacity-80">Uploading asset...</span>
            </div>
          )}

          {uploadError && (
            <div className="flex items-center gap-2 mb-3 px-1 text-danger-red">
              <AlertTriangle className="w-3 h-3" />
              <span className="text-[10px] font-mono tracking-widest uppercase">{uploadError}</span>
            </div>
          )}

          {/* Mobile quick suggestions */}
          <div className="lg:hidden flex gap-2 mb-3 overflow-x-auto pb-1 scrollbar-hide">
            {['NIFTY outlook?', 'Analyse Reliance', 'SEBI update'].map((q) => (
              <button
                key={q}
                onClick={() => handleSuggest(q)}
                className="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-full border border-border bg-white text-[11px] text-text-secondary active:scale-95 transition-all"
              >
                <Sparkles className="w-2.5 h-2.5 text-accent-primary" />
                {q}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="flex items-end gap-3">
            <div className="relative flex-1 flex items-end gap-2 bg-background-card border border-border rounded-xl px-3 py-2.5 focus-within:border-interactive-primary/50 focus-within:ring-1 focus-within:ring-interactive-primary/20 transition-all">
              <input
                type="file"
                multiple
                accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                className="hidden"
                ref={fileInputRef}
                id="file-upload"
                onChange={handleFileChange}
              />
              <button
                type="button"
                disabled={isUploading}
                onClick={() => fileInputRef.current?.click()}
                className="p-1.5 rounded-lg text-text-muted hover:text-interactive-primary hover:bg-interactive-primary/10 transition-colors disabled:opacity-30"
                title="Attach file"
              >
                <Paperclip className="w-4 h-4" />
              </button>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={isUploading ? "Uploading file..." : "Ask anything about markets..."}
                rows={1}
                disabled={isTyping}
                className="
    flex-1
    bg-transparent
    border-none
    px-2 py-1
    text-sm
    text-gray-900
    placeholder-gray-400
    focus:outline-none
    disabled:opacity-50
    leading-relaxed
    max-h-32
    overflow-y-auto
  "
                onInput={(e) => {
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px';
                }}
              />
              {input.length > 0 && (
                <span className="shrink-0 text-[10px] font-mono text-text-muted pb-1 mb-0.5">↵</span>
              )}
            </div>

            <motion.button
              type="submit"
              disabled={(!input.trim() && selectedFiles.length === 0) || isTyping || isUploading}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.95 }}
              className="shrink-0 w-11 h-11 rounded-xl flex items-center justify-center bg-interactive-primary text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-[0_4px_20px_rgba(47,129,247,0.3)]"
            >
              {isTyping ? (
                <motion.div
                  className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </motion.button>
          </form>

          <p className="mt-3 text-center text-[10px] text-text-muted font-mono flex items-center justify-center gap-1.5">
            <Zap className="w-3 h-3 text-warning-amber opacity-60" />
            For research only · Non-SEBI Advice
          </p>
        </div>
      </div>

      <IntelligencePanel
        activeQuery={activeQuery}
        isLoading={isTyping}
        intelligence={messages[messages.length - 1]?.role === 'assistant' ? messages[messages.length - 1]?.intelligence : null}
      />
    </div>
  );
};
