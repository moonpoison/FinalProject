"use client"

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react"
import { api, type ConversationResponse, type MessageResponse } from "@/lib/api"
import { useAuth } from "./auth-context"

export interface ChatMessage {
  id: string
  senderId: string
  senderName: string
  body: string
  createdAt: string
  read: boolean
}

export interface Conversation {
  id: string
  participantIds: [string, string]
  participantNames: [string, string]
  topic?: string
  messages: ChatMessage[]
  updatedAt: string
}

interface ChatContextValue {
  conversations: Conversation[]
  isLoading: boolean
  refreshConversations: () => Promise<void>
  getOrCreate: (myId: string, myName: string, otherId: string, otherName: string, topic?: string) => Conversation
  sendMessage: (conversationId: string, senderId: string, senderName: string, body: string) => Promise<void>
  markRead: (conversationId: string, userId: string) => Promise<void>
  unreadCount: (userId: string) => number
  startConversation: (myId: string, myName: string, otherName: string, topic: string) => Promise<Conversation>
}

const ChatContext = createContext<ChatContextValue | null>(null)

function messageResponseToChatMessage(msg: MessageResponse): ChatMessage {
  return {
    id: msg.id,
    senderId: msg.sender_id,
    senderName: msg.sender_name,
    body: msg.body,
    createdAt: msg.created_at,
    read: msg.read,
  }
}

function conversationResponseToConversation(conv: ConversationResponse): Conversation {
  return {
    id: conv.id,
    participantIds: conv.participant_ids as [string, string],
    participantNames: conv.participant_names as [string, string],
    topic: conv.topic || undefined,
    messages: conv.messages.map(messageResponseToChatMessage),
    updatedAt: conv.updated_at,
  }
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const refreshConversations = useCallback(async () => {
    if (!user) return
    setIsLoading(true)
    try {
      const data = await api.getConversations()
      setConversations(data.map(conversationResponseToConversation))
    } catch {
      // Silently fail
    } finally {
      setIsLoading(false)
    }
  }, [user])

  useEffect(() => {
    if (user) {
      refreshConversations()
      // Poll for new messages every 15 seconds
      const interval = setInterval(refreshConversations, 15000)
      return () => clearInterval(interval)
    } else {
      setConversations([])
    }
  }, [user, refreshConversations])

  const getOrCreate = useCallback(
    (myId: string, myName: string, otherId: string, otherName: string, topic?: string) => {
      const existing = conversations.find(
        (c) => c.participantIds.includes(myId) && c.participantIds.includes(otherId)
      )
      if (existing) return existing
      const newConv: Conversation = {
        id: `c${Date.now()}`,
        participantIds: [myId, otherId],
        participantNames: [myName, otherName],
        topic,
        messages: [],
        updatedAt: new Date().toISOString(),
      }
      setConversations((prev) => [newConv, ...prev])
      return newConv
    },
    [conversations]
  )

  const sendMessage = useCallback(
    async (conversationId: string, senderId: string, senderName: string, body: string) => {
      try {
        const msgResponse = await api.sendMessage(conversationId, body)
        const newMsg = messageResponseToChatMessage(msgResponse)
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id !== conversationId) return c
            return { ...c, messages: [...c.messages, newMsg], updatedAt: newMsg.createdAt }
          })
        )
      } catch {
        const msg: ChatMessage = {
          id: `m${Date.now()}`,
          senderId,
          senderName,
          body,
          createdAt: new Date().toISOString(),
          read: false,
        }
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id !== conversationId) return c
            return { ...c, messages: [...c.messages, msg], updatedAt: msg.createdAt }
          })
        )
      }
    },
    []
  )

  const markRead = useCallback(async (conversationId: string, userId: string) => {
    try {
      await api.markMessagesRead(conversationId)
    } catch {
      // Silently fail
    }
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id !== conversationId) return c
        return {
          ...c,
          messages: c.messages.map((m) =>
            m.senderId !== userId ? { ...m, read: true } : m
          ),
        }
      })
    )
  }, [])

  const unreadCount = useCallback(
    (userId: string) => {
      return conversations.reduce((total, c) => {
        if (!c.participantIds.includes(userId)) return total
        return total + c.messages.filter((m) => m.senderId !== userId && !m.read).length
      }, 0)
    },
    [conversations]
  )

  const startConversation = useCallback(
    async (myId: string, myName: string, otherName: string | undefined, topic: string) => {
      const safeName = (otherName && otherName.trim()) || "판매자"
      try {
        const convResponse = await api.startConversation(safeName, topic)
        const newConv = conversationResponseToConversation(convResponse)
        setConversations((prev) => {
          const exists = prev.find((c) => c.id === newConv.id)
          if (exists) return prev
          return [newConv, ...prev]
        })
        return newConv
      } catch {
        // API 실패 시 로컬에서 임시 대화 생성 (고유 ID 사용)
        const tempId = `temp-${Date.now()}`
        return getOrCreate(myId, myName, tempId, safeName, topic)
      }
    },
    [getOrCreate]
  )

  return (
    <ChatContext.Provider value={{ conversations, isLoading, refreshConversations, getOrCreate, sendMessage, markRead, unreadCount, startConversation }}>
      {children}
    </ChatContext.Provider>
  )
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error("useChat must be used within ChatProvider")
  return ctx
}
