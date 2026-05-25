"use client"

import { useState, useRef, useEffect } from "react"
import { useAuth } from "@/contexts/auth-context"
import { useChat, type Conversation } from "@/contexts/chat-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ArrowLeft, Send, MessageSquare } from "lucide-react"

function formatTime(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) return d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })
  return d.toLocaleDateString("ko-KR", { month: "short", day: "numeric" })
}

function getOther(conv: Conversation, myId: string) {
  const idx = conv.participantIds[0] === myId ? 1 : 0
  return { id: conv.participantIds[idx], name: conv.participantNames[idx] }
}

function Avatar({ name, size = "sm" }: { name: string; size?: "sm" | "md" }) {
  const colors = ["#3b82f6", "#22c55e", "#f97316", "#a855f7", "#ef4444", "#0891b2"]
  const color = colors[name.charCodeAt(0) % colors.length]
  const dim = size === "sm" ? "w-9 h-9 text-xs" : "w-11 h-11 text-sm"
  return (
    <div
      className={`${dim} rounded-full flex items-center justify-center font-bold text-white flex-shrink-0`}
      style={{ backgroundColor: color }}
    >
      {name.slice(0, 1)}
    </div>
  )
}

// ─── Conversation List ────────────────────────────────────────────────────────
function ConversationList({
  onSelect,
}: {
  onSelect: (conv: Conversation) => void
}) {
  const { user } = useAuth()
  const { conversations, unreadCount } = useChat()

  if (!user) return null

  const myConvs = conversations
    .filter((c) => c.participantIds.includes(user.id))
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-5 border-b flex-shrink-0">
        <h2 className="text-lg font-bold">대화 목록</h2>
        <p className="text-xs text-muted-foreground mt-0.5">판매자 / 구매자 간 문의 채팅</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {myConvs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground py-20">
            <MessageSquare className="w-10 h-10 opacity-30" />
            <p className="text-sm">아직 채팅이 없습니다.</p>
          </div>
        ) : (
          myConvs.map((conv) => {
            const other = getOther(conv, user.id)
            const lastMsg = conv.messages[conv.messages.length - 1]
            const unread = conv.messages.filter((m) => m.senderId !== user.id && !m.read).length

            return (
              <button
                key={conv.id}
                onClick={() => onSelect(conv)}
                className="w-full flex items-center gap-3 px-6 py-4 hover:bg-secondary/50 transition-colors text-left border-b last:border-b-0"
              >
                <Avatar name={other.name} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <span className="font-semibold text-sm truncate">{other.name}</span>
                    {lastMsg && (
                      <span className="text-[11px] text-muted-foreground flex-shrink-0">
                        {formatTime(lastMsg.createdAt)}
                      </span>
                    )}
                  </div>
                  {conv.topic && (
                    <p className="text-[11px] text-muted-foreground truncate mb-0.5">
                      {conv.topic}
                    </p>
                  )}
                  {lastMsg && (
                    <p className="text-xs text-muted-foreground truncate">{lastMsg.body}</p>
                  )}
                </div>
                {unread > 0 && (
                  <span className="w-5 h-5 rounded-full bg-foreground text-background text-[10px] font-bold flex items-center justify-center flex-shrink-0">
                    {unread}
                  </span>
                )}
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}

// ─── Message View ─────────────────────────────────────────────────────────────
function MessageView({
  conversationId,
  onBack,
}: {
  conversationId: string
  onBack: () => void
}) {
  const { user } = useAuth()
  const { conversations, sendMessage, markRead } = useChat()
  const [input, setInput] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)

  // 항상 최신 conversation 상태를 context에서 가져옴
  const conversation = conversations.find(c => c.id === conversationId)

  const other = user && conversation ? getOther(conversation, user.id) : { id: "", name: "" }

  useEffect(() => {
    if (user && conversation) markRead(conversation.id, user.id)
  }, [conversationId, conversation?.messages.length, markRead, user, conversation])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [conversation?.messages.length])

  const handleSend = () => {
    if (!input.trim() || !user || !conversation) return
    sendMessage(conversation.id, user.id, user.name, input.trim())
    setInput("")
  }

  if (!user || !conversation) return null

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3.5 border-b flex-shrink-0">
        <button
          onClick={onBack}
          className="w-8 h-8 rounded-xl hover:bg-secondary flex items-center justify-center text-muted-foreground"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <Avatar name={other.name} />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm">{other.name}</p>
          {conversation.topic && (
            <p className="text-[11px] text-muted-foreground truncate">{conversation.topic}</p>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {conversation.messages.length === 0 && (
          <p className="text-center text-xs text-muted-foreground pt-10">
            첫 메시지를 보내보세요.
          </p>
        )}
        {conversation.messages.map((msg) => {
          const isMine = msg.senderId === user.id
          return (
            <div key={msg.id} className={`flex gap-2 ${isMine ? "flex-row-reverse" : "flex-row"}`}>
              {!isMine && <Avatar name={msg.senderName} size="sm" />}
              <div className={`max-w-[70%] space-y-1 ${isMine ? "items-end" : "items-start"} flex flex-col`}>
                {!isMine && (
                  <span className="text-[11px] text-muted-foreground px-1">{msg.senderName}</span>
                )}
                <div
                  className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                    isMine
                      ? "bg-foreground text-background rounded-tr-sm"
                      : "bg-secondary text-foreground rounded-tl-sm"
                  }`}
                >
                  {msg.body}
                </div>
                <span className="text-[10px] text-muted-foreground px-1">
                  {formatTime(msg.createdAt)}
                </span>
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex items-center gap-2 px-4 py-3 border-t flex-shrink-0">
        <Input
          placeholder="메시지 입력..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing && (e.preventDefault(), handleSend())}
          className="rounded-2xl h-10 text-sm flex-1"
        />
        <Button
          size="sm"
          onClick={handleSend}
          disabled={!input.trim()}
          className="rounded-2xl h-10 w-10 p-0 flex-shrink-0"
        >
          <Send className="w-4 h-4" />
        </Button>
      </div>
    </div>
  )
}

// ─── ChatPage (exported) ──────────────────────────────────────────────────────
export function ChatPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {selectedId ? (
        <MessageView conversationId={selectedId} onBack={() => setSelectedId(null)} />
      ) : (
        <ConversationList onSelect={(conv) => setSelectedId(conv.id)} />
      )}
    </div>
  )
}
