"use client";

import React, { useRef, useEffect, KeyboardEvent, ChangeEvent } from "react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({
  value,
  onChange,
  onSend,
  disabled = false,
  placeholder = "Input target parameters or query AI...",
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize up to 6 lines (~144px)
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 144)}px`;
  }, [value]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSend();
    }
  };

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
  };

  return (
    <div
      className="flex items-end gap-3 rounded-2xl px-4 py-3"
      style={{
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {/* Attach entity button */}
      <button
        type="button"
        className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-slate-500 hover:text-primary hover:bg-primary/10 transition-colors"
        aria-label="Attach entity"
        tabIndex={-1}
      >
        <span className="material-symbols-outlined text-lg">add_circle</span>
      </button>

      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        rows={1}
        className="flex-1 resize-none bg-transparent text-sm text-slate-200 placeholder:text-slate-600 outline-none leading-relaxed disabled:opacity-50 disabled:cursor-not-allowed"
        style={{ maxHeight: 144, overflowY: "auto" }}
      />

      {/* Voice button */}
      <button
        type="button"
        className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-slate-500 hover:text-primary hover:bg-primary/10 transition-colors"
        aria-label="Voice input"
        tabIndex={-1}
      >
        <span className="material-symbols-outlined text-lg">mic</span>
      </button>

      {/* Send button */}
      <button
        type="button"
        onClick={onSend}
        disabled={disabled || !value.trim()}
        className="shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-all disabled:opacity-30 disabled:cursor-not-allowed"
        style={{
          background: disabled || !value.trim() ? "rgba(236,91,19,0.1)" : "#ec5b13",
          color: disabled || !value.trim() ? "#ec5b13" : "#fff",
        }}
        aria-label="Send message"
      >
        <span className="material-symbols-outlined text-lg">arrow_upward</span>
      </button>
    </div>
  );
}
