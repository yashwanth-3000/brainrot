"use client";

import React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, FileText, Globe, Link2, Paperclip, Upload, X } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────
export type ModeId = "search";

export interface CharacterSelection {
  type: "existing" | "create";
  name: string;
  id?: string;
}

export interface PromptSendPayload {
  message: string;
  files?: File[];
  rawContent?: string;
  mode: ModeId | "normal";
  searchUrl?: string;
  characterSelection?: CharacterSelection | null;
}

// ── Upload Modal ───────────────────────────────────────────────────────────────
interface UploadModalProps {
  onClose: () => void;
  onConfirm: (files: File[], rawContent: string) => void;
}

function UploadModal({ onClose, onConfirm }: UploadModalProps) {
  const [rawContent, setRawContent] = React.useState("");
  const [uploadedFiles, setUploadedFiles] = React.useState<File[]>([]);
  const [dragging, setDragging] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = Array.from(e.dataTransfer.files).filter(f =>
      /\.(pdf|txt|doc|docx)$/i.test(f.name)
    );
    if (dropped.length) setUploadedFiles(prev => [...prev, ...dropped]);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? []);
    if (picked.length) setUploadedFiles(prev => [...prev, ...picked]);
    if (e.target) e.target.value = "";
  };

  const removeFile = (i: number) =>
    setUploadedFiles(prev => prev.filter((_, idx) => idx !== i));

  const handleConfirm = () => {
    onConfirm(uploadedFiles, rawContent);
    onClose();
  };

  const hasAnything = uploadedFiles.length > 0 || rawContent.trim().length > 0;

  return (
    /* Backdrop */
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 100,
        background: "rgba(15,14,18,0.45)", backdropFilter: "blur(4px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "0 16px",
      }}
    >
      <motion.div
        onClick={e => e.stopPropagation()}
        initial={{ opacity: 0, scale: 0.96, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 12 }}
        transition={{ duration: 0.2, ease: [0.44, 0, 0.56, 1] }}
        style={{
          width: "100%", maxWidth: 760,
          borderRadius: 20,
          background: "#fff",
          border: "1px solid #e0dde8",
          boxShadow: "0 24px 64px rgba(82,53,239,0.14)",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "16px 20px",
          borderBottom: "1px solid #e0dde8",
        }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#0f0e12", letterSpacing: "-0.02em" }}>
            Add context
          </span>
          <button
            onClick={onClose}
            style={{
              width: 28, height: 28, borderRadius: "50%", border: "none",
              background: "rgba(0,0,0,0.06)", cursor: "pointer",
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              color: "#5c5870",
            }}
          >
            <X size={14} />
          </button>
        </div>

        {/* Two-panel body */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", minHeight: 320 }}>

          {/* Left — Raw content */}
          <div style={{
            display: "flex", flexDirection: "column",
            borderRight: "1px solid #e0dde8",
          }}>
            <div style={{
              padding: "12px 16px 8px",
              fontSize: 11, fontWeight: 700, textTransform: "uppercase",
              letterSpacing: "0.1em", color: "#5c5870",
            }}>
              Raw content
            </div>
            <textarea
              autoFocus
              value={rawContent}
              onChange={e => setRawContent(e.target.value)}
              placeholder="Paste any text, code, or data here…"
              style={{
                flex: 1, resize: "none", border: "none", outline: "none",
                padding: "0 16px 16px",
                fontSize: 13, lineHeight: 1.6, color: "#0f0e12",
                fontFamily: "inherit", background: "transparent",
              }}
            />
          </div>

          {/* Right — File upload */}
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{
              padding: "12px 16px 8px",
              fontSize: 11, fontWeight: 700, textTransform: "uppercase",
              letterSpacing: "0.1em", color: "#5c5870",
            }}>
              Upload files
            </div>

            {/* Drop zone */}
            <div
              onDragOver={e => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                margin: "0 16px",
                flex: 1, display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center", gap: 8,
                borderRadius: 12, cursor: "pointer",
                border: `2px dashed ${dragging ? "#a78bfa" : "#c4b5fd"}`,
                background: dragging ? "#ede8ff" : "#f8f7ff",
                transition: "all 0.18s",
                padding: 16,
                minHeight: 160,
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.txt,.doc,.docx"
                style={{ display: "none" }}
                onChange={handleFileInput}
              />
              <div style={{
                width: 40, height: 40, borderRadius: "50%",
                background: "#ede8ff", display: "flex",
                alignItems: "center", justifyContent: "center",
              }}>
                <Upload size={18} style={{ color: "#5235ef" }} />
              </div>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: "#3b1fcc", textAlign: "center" }}>
                {dragging ? "Drop files here" : "Click or drag files here"}
              </p>
              <p style={{ margin: 0, fontSize: 11, color: "#9e9ab8", textAlign: "center" }}>
                PDF, TXT, DOC, DOCX
              </p>
            </div>

            {/* File list */}
            {uploadedFiles.length > 0 && (
              <div style={{ padding: "10px 16px 0", display: "flex", flexDirection: "column", gap: 6 }}>
                {uploadedFiles.map((f, i) => (
                  <div key={i} style={{
                    display: "flex", alignItems: "center", gap: 8,
                    borderRadius: 10, border: "1px solid #e0dde8",
                    background: "#fafafa", padding: "6px 10px",
                    fontSize: 12, color: "#5c5870",
                  }}>
                    <FileText size={13} style={{ flexShrink: 0, color: "#7c6aff" }} />
                    <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {f.name}
                    </span>
                    <button
                      onClick={() => removeFile(i)}
                      style={{
                        background: "rgba(0,0,0,0.06)", border: "none",
                        borderRadius: "50%", padding: 3, cursor: "pointer",
                        display: "inline-flex", color: "#9e9ab8",
                      }}
                    >
                      <X size={10} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div style={{
          display: "flex", justifyContent: "flex-end", gap: 8,
          padding: "12px 20px",
          borderTop: "1px solid #e0dde8",
        }}>
          <button
            onClick={onClose}
            style={{
              padding: "8px 18px", borderRadius: 10,
              border: "1px solid #e0dde8", background: "transparent",
              fontSize: 13, fontWeight: 500, color: "#5c5870", cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!hasAnything}
            style={{
              padding: "8px 18px", borderRadius: 10, border: "none",
              background: hasAnything ? "linear-gradient(135deg,#6d5bff 0%,#5235ef 100%)" : "rgba(0,0,0,0.08)",
              color: hasAnything ? "#fff" : "rgba(0,0,0,0.3)",
              fontSize: 13, fontWeight: 600, cursor: hasAnything ? "pointer" : "default",
              boxShadow: hasAnything ? "0 4px 14px rgba(82,53,239,0.3)" : "none",
              transition: "all 0.2s",
            }}
          >
            Add to message
          </button>
        </div>
      </motion.div>
    </div>
  );
}

// ── PromptInputBox ─────────────────────────────────────────────────────────────
interface PromptInputBoxProps {
  onSend?: (payload: PromptSendPayload) => void;
  isLoading?: boolean;
  placeholder?: string;
  className?: string;
  mode?: ModeId | null;
  onModeChange?: (mode: ModeId | null) => void;
}

export const PromptInputBox = React.forwardRef<HTMLDivElement, PromptInputBoxProps>(
  ({ onSend = () => {}, isLoading = false, placeholder = "Type your message here...", mode, onModeChange }, ref) => {
    const [input, setInput] = React.useState("");
    const [files, setFiles] = React.useState<File[]>([]);
    const [rawContent, setRawContent] = React.useState("");
    const [internalActiveMode, setInternalActiveMode] = React.useState<ModeId | null>(null);
    const [showUrlPanel, setShowUrlPanel] = React.useState(false);
    const [searchUrl, setSearchUrl] = React.useState("");
    const [showUploadModal, setShowUploadModal] = React.useState(false);
    const textareaRef = React.useRef<HTMLTextAreaElement>(null);
    const urlInputRef = React.useRef<HTMLInputElement>(null);

    const activeMode = mode !== undefined ? mode : internalActiveMode;

    const toggleSearch = () => {
      const next = activeMode === "search" ? null : "search";
      if (onModeChange) onModeChange(next);
      else setInternalActiveMode(next);
      if (next === "search") {
        setShowUrlPanel(true);
        setTimeout(() => urlInputRef.current?.focus(), 80);
      } else {
        setShowUrlPanel(false);
        setSearchUrl("");
      }
    };

    // Auto-resize textarea
    React.useEffect(() => {
      const ta = textareaRef.current;
      if (!ta) return;
      ta.style.height = "auto";
      ta.style.height = `${Math.min(ta.scrollHeight, 240)}px`;
    }, [input]);

    const handleSubmit = () => {
      const trimmed = input.trim();
      if (isLoading || (!trimmed && files.length === 0 && !rawContent.trim())) return;
      onSend({
        message: trimmed,
        files,
        rawContent: rawContent.trim() || undefined,
        mode: activeMode ?? "normal",
        searchUrl: activeMode === "search" && searchUrl.trim() ? searchUrl.trim() : undefined,
        characterSelection: null,
      });
      setInput("");
      setFiles([]);
      setRawContent("");
      setSearchUrl("");
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
    };

    const hasContent = input.trim() !== "" || files.length > 0 || rawContent.trim() !== "";
    const searchActive = activeMode === "search";
    const hasAttachment = files.length > 0 || rawContent.trim().length > 0;

    return (
      <>
        <div
          ref={ref}
          style={{
            borderRadius: 24,
            border: isLoading ? "1px solid rgba(109,91,255,0.5)" : "1px solid rgba(0,0,0,0.1)",
            background: "rgba(255,255,255,0.9)",
            padding: 8,
            boxShadow: "0 4px 24px rgba(82,53,239,0.07)",
            backdropFilter: "blur(8px)",
            transition: "border 0.3s",
          }}
        >
          {/* URL panel */}
          <AnimatePresence initial={false}>
            {showUrlPanel && (
              <motion.div
                key="url-panel"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.18, ease: [0.44, 0, 0.56, 1] }}
                style={{ overflow: "hidden" }}
              >
                <div style={{
                  display: "flex", alignItems: "center", gap: 8,
                  margin: "0 4px 8px", padding: "8px 12px",
                  borderRadius: 14, background: "#ede8ff",
                  border: "1px solid #c4b5fd",
                }}>
                  <Link2 size={14} style={{ color: "#5235ef", flexShrink: 0 }} />
                  <input
                    ref={urlInputRef}
                    type="url"
                    value={searchUrl}
                    onChange={e => setSearchUrl(e.target.value)}
                    placeholder="Paste a URL to search within (optional)"
                    onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); textareaRef.current?.focus(); } }}
                    style={{
                      flex: 1, border: "none", background: "transparent", outline: "none",
                      fontSize: 13, color: "#3b1fcc", fontFamily: "inherit",
                    }}
                  />
                  {searchUrl && (
                    <button
                      onClick={() => setSearchUrl("")}
                      style={{ background: "none", border: "none", cursor: "pointer", display: "inline-flex", padding: 2, color: "#7c6aff" }}
                    >
                      <X size={12} />
                    </button>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Attachment chips */}
          {hasAttachment && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "0 4px 8px" }}>
              {files.map((file, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 6,
                  borderRadius: 10, border: "1px solid #e0dde8",
                  background: "#f8f7ff", padding: "5px 10px",
                  fontSize: 12, color: "#5c5870",
                }}>
                  <FileText size={13} style={{ color: "#7c6aff" }} />
                  <span style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{file.name}</span>
                  <button onClick={() => setFiles(prev => prev.filter((_, idx) => idx !== i))} style={{ background: "rgba(0,0,0,0.06)", border: "none", borderRadius: "50%", padding: 3, cursor: "pointer", display: "inline-flex" }}>
                    <X size={10} />
                  </button>
                </div>
              ))}
              {rawContent.trim() && (
                <div style={{
                  display: "flex", alignItems: "center", gap: 6,
                  borderRadius: 10, border: "1px solid #e0dde8",
                  background: "#f8f7ff", padding: "5px 10px",
                  fontSize: 12, color: "#5c5870",
                }}>
                  <FileText size={13} style={{ color: "#7c6aff" }} />
                  <span>{rawContent.trim().length} chars of raw text</span>
                  <button onClick={() => setRawContent("")} style={{ background: "rgba(0,0,0,0.06)", border: "none", borderRadius: "50%", padding: 3, cursor: "pointer", display: "inline-flex" }}>
                    <X size={10} />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
            placeholder={searchActive ? "What do you want to search for?" : placeholder}
            style={{
              display: "block", width: "100%", boxSizing: "border-box",
              resize: "none", border: "none", background: "transparent", outline: "none",
              fontSize: 16, lineHeight: 1.5, color: "#1a1a1a",
              padding: "10px 12px", minHeight: 44, fontFamily: "inherit",
            }}
          />

          {/* Action bar */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, paddingTop: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>

              {/* Paperclip — always visible */}
              <button
                onClick={() => setShowUploadModal(true)}
                disabled={isLoading}
                title="Add content"
                style={{
                  width: 32, height: 32, borderRadius: "50%",
                  border: hasAttachment ? "1px solid #a78bfa" : "1px solid transparent",
                  background: hasAttachment ? "#ede8ff" : "transparent",
                  cursor: "pointer",
                  display: "inline-flex", alignItems: "center", justifyContent: "center",
                  color: hasAttachment ? "#5235ef" : "rgba(0,0,0,0.4)",
                  transition: "all 0.2s",
                }}
              >
                <Paperclip size={15} />
              </button>

              {/* Divider */}
              <div style={{ height: 20, width: 1, background: "rgba(0,0,0,0.12)", borderRadius: 999 }} />

              {/* Web Search */}
              <button
                type="button"
                onClick={toggleSearch}
                style={{
                  display: "inline-flex", alignItems: "center", gap: 6,
                  borderRadius: 999, padding: "4px 12px", height: 32,
                  fontSize: 12, fontWeight: 500, cursor: "pointer",
                  transition: "all 0.2s",
                  ...(searchActive
                    ? { background: "#ede8ff", border: "1px solid #a78bfa", color: "#5235ef" }
                    : { background: "transparent", border: "1px solid transparent", color: "rgba(0,0,0,0.45)" }),
                }}
              >
                <Globe size={14} />
                <span>Web Search</span>
              </button>

              {/* Divider */}
              <div style={{ height: 20, width: 1, background: "rgba(0,0,0,0.12)", borderRadius: 999 }} />

              {/* Upload button */}
              <button
                type="button"
                onClick={() => setShowUploadModal(true)}
                disabled={isLoading}
                style={{
                  display: "inline-flex", alignItems: "center", gap: 6,
                  borderRadius: 999, padding: "4px 12px", height: 32,
                  fontSize: 12, fontWeight: 500, cursor: "pointer",
                  transition: "all 0.2s",
                  ...(hasAttachment
                    ? { background: "#ede8ff", border: "1px solid #a78bfa", color: "#5235ef" }
                    : { background: "transparent", border: "1px solid transparent", color: "rgba(0,0,0,0.45)" }),
                }}
              >
                <Upload size={14} />
                <span>Upload</span>
              </button>
            </div>

            {/* Send button */}
            <button
              onClick={handleSubmit}
              disabled={isLoading || !hasContent}
              style={{
                width: 32, height: 32, borderRadius: "50%", border: "none",
                cursor: hasContent ? "pointer" : "default",
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                background: hasContent ? "linear-gradient(135deg, #6d5bff 0%, #5235ef 100%)" : "rgba(0,0,0,0.08)",
                color: hasContent ? "#fff" : "rgba(0,0,0,0.35)",
                boxShadow: hasContent ? "0 4px 14px rgba(82,53,239,0.35)" : "none",
                transition: "all 0.2s",
                opacity: isLoading ? 0.6 : 1,
              }}
            >
              <ArrowUp size={16} />
            </button>
          </div>
        </div>

        {/* Upload Modal */}
        <AnimatePresence>
          {showUploadModal && (
            <UploadModal
              onClose={() => setShowUploadModal(false)}
              onConfirm={(newFiles, newRaw) => {
                if (newFiles.length) setFiles(prev => [...prev, ...newFiles]);
                if (newRaw.trim()) setRawContent(newRaw);
              }}
            />
          )}
        </AnimatePresence>
      </>
    );
  }
);
PromptInputBox.displayName = "PromptInputBox";
