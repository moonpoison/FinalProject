"use client"

import { useState, useEffect, useMemo } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import {
  ChevronDown,
  ChevronRight,
  Variable,
  Key,
  Globe,
  User,
  Lock,
  FileText,
  Hash,
  AtSign,
} from "lucide-react"
import type { WorkspaceBlock } from "@/types/blocks"

interface DetectedVariable {
  name: string
  type: "text" | "password" | "url" | "number" | "email"
  description: string
  defaultValue?: string
  source: string // 어느 블록에서 감지됐는지
  icon: React.ReactNode
}

interface VariablesPanelProps {
  blocks: WorkspaceBlock[]
  variables: Record<string, string>
  onVariablesChange: (variables: Record<string, string>) => void
}

// 변수 패턴 감지 규칙
const VARIABLE_PATTERNS: { pattern: RegExp; name: string; type: DetectedVariable["type"]; description: string }[] = [
  { pattern: /\{\{?\s*(username|user_?name|user_?id|아이디|사용자명)\s*\}?\}/gi, name: "username", type: "text", description: "로그인 아이디" },
  { pattern: /\{\{?\s*(password|passwd|pwd|비밀번호|비번)\s*\}?\}/gi, name: "password", type: "password", description: "비밀번호" },
  { pattern: /\{\{?\s*(email|이메일|메일)\s*\}?\}/gi, name: "email", type: "email", description: "이메일 주소" },
  { pattern: /\{\{?\s*(search_?keyword|keyword|검색어|키워드|query)\s*\}?\}/gi, name: "search_keyword", type: "text", description: "검색어" },
  { pattern: /\{\{?\s*(url|link|주소|링크|사이트)\s*\}?\}/gi, name: "url", type: "url", description: "URL 주소" },
  { pattern: /\{\{?\s*(count|num|number|횟수|개수|반복)\s*\}?\}/gi, name: "count", type: "number", description: "반복 횟수" },
  { pattern: /\{\{?\s*(filename|file_?name|파일명|파일이름)\s*\}?\}/gi, name: "filename", type: "text", description: "파일명" },
  { pattern: /\{\{?\s*(message|msg|메시지|내용|텍스트|text|content)\s*\}?\}/gi, name: "message", type: "text", description: "입력 텍스트" },
]

// 필드명으로 변수 감지
const FIELD_VARIABLE_MAP: Record<string, { type: DetectedVariable["type"]; description: string }> = {
  "username": { type: "text", description: "로그인 아이디" },
  "password": { type: "password", description: "비밀번호" },
  "email": { type: "email", description: "이메일 주소" },
  "text": { type: "text", description: "입력 텍스트" },
  "url": { type: "url", description: "URL 주소" },
  "count": { type: "number", description: "반복 횟수" },
  "filename": { type: "text", description: "파일명" },
  "query": { type: "text", description: "검색어" },
  "keyword": { type: "text", description: "키워드" },
}

function getVariableIcon(type: DetectedVariable["type"]) {
  switch (type) {
    case "password": return <Lock className="w-3.5 h-3.5" />
    case "url": return <Globe className="w-3.5 h-3.5" />
    case "email": return <AtSign className="w-3.5 h-3.5" />
    case "number": return <Hash className="w-3.5 h-3.5" />
    default: return <FileText className="w-3.5 h-3.5" />
  }
}

export function VariablesPanel({ blocks, variables, onVariablesChange }: VariablesPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  // 블록에서 변수 감지
  const detectedVariables = useMemo(() => {
    const vars: DetectedVariable[] = []
    const seenNames = new Set<string>()

    blocks.forEach((block) => {
      const fieldValues = block.fieldValues || {}

      // 필드 값에서 {{variable}} 패턴 찾기
      Object.entries(fieldValues).forEach(([fieldName, value]) => {
        if (typeof value !== "string") return

        // 패턴 매칭으로 변수 찾기
        VARIABLE_PATTERNS.forEach(({ pattern, name, type, description }) => {
          if (pattern.test(value) && !seenNames.has(name)) {
            seenNames.add(name)
            vars.push({
              name,
              type,
              description,
              defaultValue: "",
              source: block.label,
              icon: getVariableIcon(type),
            })
          }
          // 패턴 리셋 (global flag 때문에)
          pattern.lastIndex = 0
        })

        // 필드명이 변수를 나타내는 경우 (예: username, password 필드에 빈 값)
        const lowerField = fieldName.toLowerCase()
        if (FIELD_VARIABLE_MAP[lowerField] && !value && !seenNames.has(lowerField)) {
          seenNames.add(lowerField)
          const mapping = FIELD_VARIABLE_MAP[lowerField]
          vars.push({
            name: lowerField,
            type: mapping.type,
            description: mapping.description,
            defaultValue: "",
            source: block.label,
            icon: getVariableIcon(mapping.type),
          })
        }
      })

      // 로그인 관련 블록 감지
      if (block.id === "input-text" || block.label?.includes("로그인") || block.label?.includes("입력")) {
        const selector = (fieldValues.selector || "").toLowerCase()
        const text = fieldValues.text || ""

        // 비밀번호 필드 감지
        if ((selector.includes("password") || selector.includes("pwd")) && !seenNames.has("password")) {
          if (!text || text.includes("{{")) {
            seenNames.add("password")
            vars.push({
              name: "password",
              type: "password",
              description: "비밀번호",
              defaultValue: "",
              source: block.label,
              icon: <Lock className="w-3.5 h-3.5" />,
            })
          }
        }

        // 아이디 필드 감지
        if ((selector.includes("user") || selector.includes("id") || selector.includes("email") || selector.includes("login")) && !seenNames.has("username")) {
          if (!text || text.includes("{{")) {
            seenNames.add("username")
            vars.push({
              name: "username",
              type: "text",
              description: "로그인 아이디",
              defaultValue: "",
              source: block.label,
              icon: <User className="w-3.5 h-3.5" />,
            })
          }
        }
      }

      // 검색 블록 감지
      if (block.label?.includes("검색") || block.id === "input-text") {
        const selector = (fieldValues.selector || "").toLowerCase()
        const text = fieldValues.text || ""

        if ((selector.includes("search") || selector.includes("query") || selector.includes("keyword")) && !seenNames.has("search_keyword")) {
          if (!text || text.includes("{{") || text === "검색어를 입력하세요") {
            seenNames.add("search_keyword")
            vars.push({
              name: "search_keyword",
              type: "text",
              description: "검색어",
              defaultValue: "",
              source: block.label,
              icon: <FileText className="w-3.5 h-3.5" />,
            })
          }
        }
      }

      // 반복 블록 감지
      if (block.id === "loop") {
        const count = fieldValues.count
        if (!count || count === "{{count}}" || count === "0") {
          if (!seenNames.has("loop_count")) {
            seenNames.add("loop_count")
            vars.push({
              name: "loop_count",
              type: "number",
              description: "반복 횟수",
              defaultValue: "10",
              source: block.label,
              icon: <Hash className="w-3.5 h-3.5" />,
            })
          }
        }
      }
    })

    return vars
  }, [blocks])

  // 변수값 업데이트
  const handleVariableChange = (name: string, value: string) => {
    onVariablesChange({
      ...variables,
      [name]: value,
    })
  }

  if (detectedVariables.length === 0) {
    return null
  }

  return (
    <div className="border-t bg-background">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Variable className="w-4 h-4 text-primary" />
          <span className="text-xs font-medium">변수 입력</span>
          <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full">
            {detectedVariables.length}
          </span>
        </div>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-2">
          {detectedVariables.map((variable) => (
            <div key={variable.name} className="space-y-1">
              <Label className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                {variable.icon}
                {variable.description}
              </Label>
              <Input
                type={variable.type === "password" ? "password" : variable.type === "number" ? "number" : "text"}
                placeholder={variable.description}
                value={variables[variable.name] || ""}
                onChange={(e) => handleVariableChange(variable.name, e.target.value)}
                className="h-7 text-xs rounded-lg"
              />
            </div>
          ))}
          <p className="text-[10px] text-muted-foreground pt-1">
            실행 시 블록에 자동 적용됩니다
          </p>
        </div>
      )}
    </div>
  )
}
