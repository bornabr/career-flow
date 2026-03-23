import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { ChatComposer } from "../chat-composer"

describe("ChatComposer", () => {
  it("renders input and button", () => {
    render(
      <ChatComposer
        value=""
        onChange={() => {}}
        onSend={() => {}}
      />
    )
    
    expect(screen.getByPlaceholderText("Type your message...")).toBeDefined()
    expect(screen.getByRole("button", { name: /send message/i })).toBeDefined()
  })

  it("calls onChange when typing", () => {
    const onChange = vi.fn()
    render(
      <ChatComposer
        value=""
        onChange={onChange}
        onSend={() => {}}
      />
    )
    
    const input = screen.getByPlaceholderText("Type your message...")
    fireEvent.change(input, { target: { value: "Hello" } })
    
    expect(onChange).toHaveBeenCalledWith("Hello")
  })

  it("calls onSend when Enter key is pressed", () => {
    const onSend = vi.fn()
    render(
      <ChatComposer
        value="Hello"
        onChange={() => {}}
        onSend={onSend}
      />
    )
    
    const input = screen.getByPlaceholderText("Type your message...")
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" })
    
    expect(onSend).toHaveBeenCalled()
  })

  it("does not call onSend when Shift+Enter is pressed", () => {
    const onSend = vi.fn()
    render(
      <ChatComposer
        value="Hello"
        onChange={() => {}}
        onSend={onSend}
      />
    )
    
    const input = screen.getByPlaceholderText("Type your message...")
    fireEvent.keyDown(input, { key: "Enter", code: "Enter", shiftKey: true })
    
    expect(onSend).not.toHaveBeenCalled()
  })

  it("disables input and button when disabled prop is true", () => {
    render(
      <ChatComposer
        value=""
        onChange={() => {}}
        onSend={() => {}}
        disabled={true}
      />
    )
    
    const input = screen.getByPlaceholderText("Type your message...") as HTMLInputElement
    const button = screen.getByRole("button", { name: /send message/i }) as HTMLButtonElement
    
    expect(input.disabled).toBe(true)
    expect(button.disabled).toBe(true)
  })
})
