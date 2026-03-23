import * as React from "react"
import { Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface ChatComposerProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled?: boolean
  placeholder?: string
}

export function ChatComposer({
  value,
  onChange,
  onSend,
  disabled,
  placeholder = "Type your message...",
}: ChatComposerProps) {
  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      onSend()
    }
  }

  return (
    <div className="flex w-full items-center gap-2">
      <Input
        autoFocus
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        className="flex-1"
      />
      <Button
        type="button"
        size="icon"
        disabled={disabled || !value.trim()}
        onClick={onSend}
      >
        <Send className="size-4" />
        <span className="sr-only">Send message</span>
      </Button>
    </div>
  )
}
