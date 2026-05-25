export interface BlockField {
  name: string
  type: 'text' | 'number' | 'select' | 'selector'
  label: string
  placeholder?: string
  options?: { value: string; label: string }[]
  value?: string | number
}

export interface BlockDefinition {
  id: string
  type: string
  category: BlockCategory
  label: string
  icon: string
  color: string
  fields: BlockField[]
}

export interface WorkspaceBlock extends BlockDefinition {
  instanceId: string
  fieldValues: Record<string, string | number>
  /** 워크플로우 그룹 ID (AI 생성 시 부여) */
  groupId?: string
  /** 워크플로우 그룹 이름 */
  groupLabel?: string
  /** 그룹 색상 */
  groupColor?: string
}

export type BlockCategory = 'start' | 'browser' | 'action' | 'data' | 'control' | 'keyboard' | 'tab' | 'api' | 'advanced' | 'desktop'

export const BLOCK_CATEGORIES: Record<BlockCategory, { label: string; color: string }> = {
  start:    { label: '시작',      color: '#22c55e' },
  browser:  { label: '브라우저',  color: '#3b82f6' },
  tab:      { label: '탭/창',     color: '#06b6d4' },
  action:   { label: '마우스',    color: '#eab308' },
  keyboard: { label: '키보드',    color: '#f43f5e' },
  data:     { label: '데이터',    color: '#a855f7' },
  control:  { label: '제어',      color: '#f97316' },
  api:      { label: 'API/HTTP',  color: '#10b981' },
  desktop:  { label: '데스크톱',  color: '#ec4899' },
  advanced: { label: '고급',      color: '#6366f1' },
}

export const BLOCK_DEFINITIONS: BlockDefinition[] = [
  // ── 시작 ─────────────────────────────────────────────────
  {
    id: 'start',
    type: 'start',
    category: 'start',
    label: '시작하기',
    icon: 'play',
    color: '#22c55e',
    fields: [],
  },
  {
    id: 'schedule',
    type: 'schedule',
    category: 'start',
    label: '예약 실행',
    icon: 'calendar-clock',
    color: '#16a34a',
    fields: [
      {
        name: 'cron',
        type: 'select',
        label: '실행 주기',
        options: [
          { value: 'every_minute', label: '매 분마다' },
          { value: 'every_hour',   label: '매 시간마다' },
          { value: 'every_day',    label: '매일 자정' },
          { value: 'every_week',   label: '매주 월요일' },
        ],
        value: 'every_day',
      },
    ],
  },

  // ── 브라우저 ─────────────────────────────────────────────
  {
    id: 'open-site',
    type: 'open-site',
    category: 'browser',
    label: '사이트 열기',
    icon: 'globe',
    color: '#3b82f6',
    fields: [
      { name: 'url', type: 'text', label: 'URL', placeholder: 'https://example.com' },
    ],
  },
  {
    id: 'navigate',
    type: 'navigate',
    category: 'browser',
    label: '페이지 이동',
    icon: 'arrow-right',
    color: '#3b82f6',
    fields: [
      { name: 'url', type: 'text', label: 'URL', placeholder: '/page' },
    ],
  },
  {
    id: 'reload',
    type: 'reload',
    category: 'browser',
    label: '새로고침',
    icon: 'refresh-cw',
    color: '#2563eb',
    fields: [],
  },
  {
    id: 'go-back',
    type: 'go-back',
    category: 'browser',
    label: '뒤로가기',
    icon: 'arrow-left',
    color: '#2563eb',
    fields: [],
  },
  {
    id: 'go-forward',
    type: 'go-forward',
    category: 'browser',
    label: '앞으로가기',
    icon: 'arrow-right-circle',
    color: '#2563eb',
    fields: [],
  },
  {
    id: 'scroll',
    type: 'scroll',
    category: 'browser',
    label: '스크롤',
    icon: 'move-vertical',
    color: '#1d4ed8',
    fields: [
      {
        name: 'direction',
        type: 'select',
        label: '방향',
        options: [
          { value: 'down',   label: '아래로' },
          { value: 'up',     label: '위로' },
          { value: 'bottom', label: '맨 아래로' },
          { value: 'top',    label: '맨 위로' },
        ],
        value: 'down',
      },
      { name: 'amount', type: 'number', label: '픽셀 (px)', placeholder: '500' },
    ],
  },
  {
    id: 'wait-page-load',
    type: 'wait-page-load',
    category: 'browser',
    label: '페이지 로드 대기',
    icon: 'loader',
    color: '#1d4ed8',
    fields: [
      { name: 'timeout', type: 'number', label: '최대 대기(초)', placeholder: '30' },
    ],
  },
  {
    id: 'wait-element',
    type: 'wait-element',
    category: 'browser',
    label: '요소 나타날 때까지 대기',
    icon: 'scan-search',
    color: '#1e40af',
    fields: [
      { name: 'selector', type: 'selector', label: '선택자', placeholder: '#modal' },
      { name: 'timeout',  type: 'number',   label: '최대 대기(초)', placeholder: '10' },
    ],
  },
  {
    id: 'screenshot',
    type: 'screenshot',
    category: 'browser',
    label: '스크린샷 저장',
    icon: 'camera',
    color: '#1e40af',
    fields: [
      { name: 'filename', type: 'text', label: '파일명', placeholder: 'screenshot.png' },
      {
        name: 'area',
        type: 'select',
        label: '영역',
        options: [
          { value: 'full',    label: '전체 페이지' },
          { value: 'visible', label: '화면에 보이는 영역' },
          { value: 'element', label: '특정 요소' },
        ],
        value: 'visible',
      },
    ],
  },

  // ── 탭/창 ────────────────────────────────────────────────
  {
    id: 'new-tab',
    type: 'new-tab',
    category: 'tab',
    label: '새 탭 열기',
    icon: 'panel-top-open',
    color: '#06b6d4',
    fields: [
      { name: 'url', type: 'text', label: 'URL (선택)', placeholder: 'https://example.com' },
    ],
  },
  {
    id: 'close-tab',
    type: 'close-tab',
    category: 'tab',
    label: '탭 닫기',
    icon: 'x-circle',
    color: '#0891b2',
    fields: [],
  },
  {
    id: 'switch-tab',
    type: 'switch-tab',
    category: 'tab',
    label: '탭 전환',
    icon: 'layout-grid',
    color: '#0891b2',
    fields: [
      { name: 'index', type: 'number', label: '탭 번호 (0부터)', placeholder: '0' },
    ],
  },
  {
    id: 'switch-frame',
    type: 'switch-frame',
    category: 'tab',
    label: 'iframe 전환',
    icon: 'frame',
    color: '#0e7490',
    fields: [
      { name: 'selector', type: 'selector', label: 'iframe 선택자', placeholder: '#iframe-id' },
    ],
  },

  // ── 마우스 액션 ──────────────────────────────────────────
  {
    id: 'click',
    type: 'click',
    category: 'action',
    label: '클릭',
    icon: 'mouse-pointer',
    color: '#eab308',
    fields: [
      { name: 'selector', type: 'selector', label: '선택자', placeholder: '#button-id' },
    ],
  },
  {
    id: 'double-click',
    type: 'double-click',
    category: 'action',
    label: '더블 클릭',
    icon: 'mouse-pointer-2',
    color: '#ca8a04',
    fields: [
      { name: 'selector', type: 'selector', label: '선택자', placeholder: '.item' },
    ],
  },
  {
    id: 'right-click',
    type: 'right-click',
    category: 'action',
    label: '우클릭',
    icon: 'mouse-pointer-click',
    color: '#ca8a04',
    fields: [
      { name: 'selector', type: 'selector', label: '선택자', placeholder: '.context-target' },
    ],
  },
  {
    id: 'hover',
    type: 'hover',
    category: 'action',
    label: '마우스 올리기',
    icon: 'scan',
    color: '#a16207',
    fields: [
      { name: 'selector', type: 'selector', label: '선택자', placeholder: '.dropdown' },
    ],
  },
  {
    id: 'drag-drop',
    type: 'drag-drop',
    category: 'action',
    label: '드래그 앤 드롭',
    icon: 'hand',
    color: '#a16207',
    fields: [
      { name: 'source', type: 'selector', label: '출발지 선택자', placeholder: '#draggable' },
      { name: 'target', type: 'selector', label: '목적지 선택자', placeholder: '#droptarget' },
    ],
  },
  {
    id: 'select-option',
    type: 'select-option',
    category: 'action',
    label: '드롭다운 선택',
    icon: 'list',
    color: '#eab308',
    fields: [
      { name: 'selector', type: 'selector', label: '선택자', placeholder: 'select#country' },
      { name: 'value',    type: 'text',     label: '값',     placeholder: 'KR' },
    ],
  },
  {
    id: 'check-checkbox',
    type: 'check-checkbox',
    category: 'action',
    label: '체크박스 선택',
    icon: 'check-square',
    color: '#eab308',
    fields: [
      { name: 'selector', type: 'selector', label: '선택자', placeholder: '#agree' },
      {
        name: 'state',
        type: 'select',
        label: '상태',
        options: [
          { value: 'check',   label: '체크' },
          { value: 'uncheck', label: '체크 해제' },
          { value: 'toggle',  label: '토글' },
        ],
        value: 'check',
      },
    ],
  },
  {
    id: 'upload-file',
    type: 'upload-file',
    category: 'action',
    label: '파일 업로드',
    icon: 'upload',
    color: '#ca8a04',
    fields: [
      { name: 'selector', type: 'selector', label: '파일 입력 선택자', placeholder: 'input[type=file]' },
      { name: 'filepath', type: 'text',     label: '파일 경로',        placeholder: 'C:/files/doc.pdf' },
    ],
  },

  // ── 키보드 ───────────────────────────────────────────────
  {
    id: 'input-text',
    type: 'input-text',
    category: 'keyboard',
    label: '텍스트 입력',
    icon: 'keyboard',
    color: '#f43f5e',
    fields: [
      { name: 'selector', type: 'selector', label: '선택자', placeholder: '#input-id' },
      { name: 'text',     type: 'text',     label: '입력 텍스트', placeholder: '입력할 내용' },
      {
        name: 'clear',
        type: 'select',
        label: '기존 내용',
        options: [
          { value: 'clear',  label: '지우고 입력' },
          { value: 'append', label: '이어서 입력' },
        ],
        value: 'clear',
      },
    ],
  },
  {
    id: 'press-key',
    type: 'press-key',
    category: 'keyboard',
    label: '키 누르기',
    icon: 'command',
    color: '#e11d48',
    fields: [
      {
        name: 'key',
        type: 'select',
        label: '키',
        options: [
          { value: 'Enter',     label: 'Enter' },
          { value: 'Tab',       label: 'Tab' },
          { value: 'Escape',    label: 'Escape' },
          { value: 'Backspace', label: 'Backspace' },
          { value: 'Delete',    label: 'Delete' },
          { value: 'ArrowDown', label: '방향키 아래' },
        ],
        value: 'Enter',
      },
    ],
  },
  {
    id: 'shortcut',
    type: 'shortcut',
    category: 'keyboard',
    label: '단축키 실행',
    icon: 'zap',
    color: '#be123c',
    fields: [
      {
        name: 'shortcut',
        type: 'select',
        label: '단축키',
        options: [
          { value: 'Ctrl+A', label: 'Ctrl+A (전체 선택)' },
          { value: 'Ctrl+C', label: 'Ctrl+C (복사)' },
          { value: 'Ctrl+V', label: 'Ctrl+V (붙여넣기)' },
          { value: 'Ctrl+Z', label: 'Ctrl+Z (실행 취소)' },
          { value: 'Ctrl+S', label: 'Ctrl+S (저장)' },
        ],
        value: 'Ctrl+C',
      },
    ],
  },
  {
    id: 'clear-field',
    type: 'clear-field',
    category: 'keyboard',
    label: '입력 필드 지우기',
    icon: 'eraser',
    color: '#be123c',
    fields: [
      { name: 'selector', type: 'selector', label: '선택자', placeholder: '#search-input' },
    ],
  },

  // ── 데이터 ───────────────────────────────────────────────
  {
    id: 'extract-text',
    type: 'extract-text',
    category: 'data',
    label: '텍스트 추출',
    icon: 'text-cursor',
    color: '#a855f7',
    fields: [
      { name: 'selector', type: 'selector', label: '선택자', placeholder: '.price' },
      { name: 'variable', type: 'text',     label: '저장 변수명', placeholder: 'price' },
    ],
  },
  {
    id: 'extract-list',
    type: 'extract-list',
    category: 'data',
    label: '목록 추출 (반복)',
    icon: 'rows',
    color: '#9333ea',
    fields: [
      { name: 'selector',  type: 'selector', label: '반복 항목 선택자', placeholder: '.product-item' },
      { name: 'fields',    type: 'text',     label: '추출 필드 (콤마 구분)', placeholder: 'name, price, link' },
      { name: 'variable',  type: 'text',     label: '저장 변수명', placeholder: 'products' },
    ],
  },
  {
    id: 'extract-attr',
    type: 'extract-attr',
    category: 'data',
    label: '속성값 추출',
    icon: 'code-xml',
    color: '#9333ea',
    fields: [
      { name: 'selector',  type: 'selector', label: '선택자', placeholder: 'a.link' },
      { name: 'attribute', type: 'text',     label: '속성명',  placeholder: 'href' },
      { name: 'variable',  type: 'text',     label: '저장 변수명', placeholder: 'url' },
    ],
  },
  {
    id: 'save-excel',
    type: 'save-excel',
    category: 'data',
    label: '엑셀로 저장',
    icon: 'file-spreadsheet',
    color: '#7c3aed',
    fields: [
      { name: 'variable', type: 'text', label: '저장할 변수명', placeholder: 'products' },
      { name: 'filename', type: 'text', label: '파일명',       placeholder: 'result.xlsx' },
      {
        name: 'mode',
        type: 'select',
        label: '저장 방식',
        options: [
          { value: 'overwrite', label: '덮어쓰기' },
          { value: 'append',    label: '이어쓰기' },
        ],
        value: 'overwrite',
      },
    ],
  },
  {
    id: 'save-csv',
    type: 'save-csv',
    category: 'data',
    label: 'CSV로 저장',
    icon: 'file-text',
    color: '#7c3aed',
    fields: [
      { name: 'variable', type: 'text', label: '저장할 변수명', placeholder: 'data' },
      { name: 'filename', type: 'text', label: '파일명',       placeholder: 'result.csv' },
    ],
  },
  {
    id: 'set-variable',
    type: 'set-variable',
    category: 'data',
    label: '변수 설정',
    icon: 'variable',
    color: '#6d28d9',
    fields: [
      { name: 'name',  type: 'text', label: '변수명', placeholder: 'counter' },
      { name: 'value', type: 'text', label: '값',     placeholder: '0' },
    ],
  },
  {
    id: 'read-excel',
    type: 'read-excel',
    category: 'data',
    label: '엑셀 읽기',
    icon: 'file-input',
    color: '#6d28d9',
    fields: [
      { name: 'filepath', type: 'text',   label: '파일 경로', placeholder: 'C:/data/input.xlsx' },
      { name: 'sheet',    type: 'text',   label: '시트명',    placeholder: 'Sheet1' },
      { name: 'variable', type: 'text',   label: '저장 변수명', placeholder: 'rows' },
    ],
  },
  {
    id: 'send-email',
    type: 'send-email',
    category: 'data',
    label: '이메일 전송',
    icon: 'mail',
    color: '#7c3aed',
    fields: [
      { name: 'to',      type: 'text', label: '받는 사람',  placeholder: 'to@example.com' },
      { name: 'subject', type: 'text', label: '제목',       placeholder: '자동화 결과 보고서' },
      { name: 'body',    type: 'text', label: '내용',       placeholder: '결과를 첨부합니다.' },
      { name: 'attach',  type: 'text', label: '첨부 변수 (선택)', placeholder: 'result.xlsx' },
    ],
  },
  {
    id: 'send-slack',
    type: 'send-slack',
    category: 'data',
    label: 'Slack 알림',
    icon: 'message-square',
    color: '#6d28d9',
    fields: [
      { name: 'channel', type: 'text', label: '채널', placeholder: '#general' },
      { name: 'message', type: 'text', label: '메시지', placeholder: '자동화 완료!' },
    ],
  },

  // ── 제어 ────────────────────────────────────────────────
  {
    id: 'wait',
    type: 'wait',
    category: 'control',
    label: '기다리기',
    icon: 'clock',
    color: '#f97316',
    fields: [
      { name: 'seconds', type: 'number', label: '초', placeholder: '3' },
    ],
  },
  {
    id: 'loop',
    type: 'loop',
    category: 'control',
    label: '횟수 반복',
    icon: 'repeat',
    color: '#ea580c',
    fields: [
      { name: 'count', type: 'number', label: '반복 횟수', placeholder: '5' },
    ],
  },
  {
    id: 'loop-list',
    type: 'loop-list',
    category: 'control',
    label: '목록 반복',
    icon: 'list-ordered',
    color: '#ea580c',
    fields: [
      { name: 'variable', type: 'text', label: '반복할 변수명', placeholder: 'rows' },
      { name: 'item',     type: 'text', label: '항목 변수명',   placeholder: 'row' },
    ],
  },
  {
    id: 'condition',
    type: 'condition',
    category: 'control',
    label: '조건문 (if)',
    icon: 'git-branch',
    color: '#f97316',
    fields: [
      { name: 'left',     type: 'text',     label: '좌항',    placeholder: '{{price}}' },
      {
        name: 'operator',
        type: 'select',
        label: '연산자',
        options: [
          { value: '==',       label: '같음 (==)' },
          { value: '!=',       label: '다름 (!=)' },
          { value: '>',        label: '초과 (>)' },
          { value: '<',        label: '미만 (<)' },
          { value: 'contains', label: '포함 (contains)' },
          { value: 'exists',   label: '요소 존재 (exists)' },
        ],
        value: '==',
      },
      { name: 'right', type: 'text', label: '우항', placeholder: '10000' },
    ],
  },
  {
    id: 'stop-if',
    type: 'stop-if',
    category: 'control',
    label: '조건 충족 시 중단',
    icon: 'octagon',
    color: '#dc2626',
    fields: [
      { name: 'condition', type: 'text', label: '중단 조건', placeholder: '{{count}} >= 100' },
    ],
  },
  {
    id: 'break-loop',
    type: 'break-loop',
    category: 'control',
    label: '반복 중단',
    icon: 'square-x',
    color: '#dc2626',
    fields: [],
  },
  {
    id: 'log',
    type: 'log',
    category: 'control',
    label: '로그 출력',
    icon: 'terminal',
    color: '#c2410c',
    fields: [
      { name: 'message', type: 'text', label: '메시지', placeholder: '처리 중: {{item.name}}' },
      {
        name: 'level',
        type: 'select',
        label: '레벨',
        options: [
          { value: 'info',    label: 'INFO' },
          { value: 'success', label: 'SUCCESS' },
          { value: 'warning', label: 'WARNING' },
          { value: 'error',   label: 'ERROR' },
        ],
        value: 'info',
      },
    ],
  },
  {
    id: 'try-catch',
    type: 'try-catch',
    category: 'control',
    label: '오류 처리 (try)',
    icon: 'shield-alert',
    color: '#b45309',
    fields: [
      {
        name: 'on_error',
        type: 'select',
        label: '오류 발생 시',
        options: [
          { value: 'continue', label: '계속 진행' },
          { value: 'stop',     label: '실행 중단' },
          { value: 'retry',    label: '재시도' },
        ],
        value: 'continue',
      },
      { name: 'retries', type: 'number', label: '재시도 횟수', placeholder: '3' },
    ],
  },

  // ── API / HTTP ────────────────────────────────────────────────────────
  {
    id: 'http-request',
    type: 'http-request',
    category: 'api',
    label: 'HTTP 요청',
    icon: 'globe-2',
    color: '#10b981',
    fields: [
      {
        name: 'method',
        type: 'select',
        label: '메서드',
        options: [
          { value: 'GET',    label: 'GET' },
          { value: 'POST',   label: 'POST' },
          { value: 'PUT',    label: 'PUT' },
          { value: 'PATCH',  label: 'PATCH' },
          { value: 'DELETE', label: 'DELETE' },
        ],
        value: 'GET',
      },
      { name: 'url',      type: 'text', label: 'URL',         placeholder: 'https://api.example.com/data' },
      { name: 'variable', type: 'text', label: '응답 저장 변수', placeholder: 'response' },
    ],
  },
  {
    id: 'http-headers',
    type: 'http-headers',
    category: 'api',
    label: 'HTTP 헤더 설정',
    icon: 'list-tree',
    color: '#059669',
    fields: [
      { name: 'key',   type: 'text', label: '헤더 키',  placeholder: 'Authorization' },
      { name: 'value', type: 'text', label: '헤더 값',  placeholder: 'Bearer {{token}}' },
    ],
  },
  {
    id: 'http-body',
    type: 'http-body',
    category: 'api',
    label: 'HTTP 바디 설정',
    icon: 'braces',
    color: '#059669',
    fields: [
      {
        name: 'content_type',
        type: 'select',
        label: '타입',
        options: [
          { value: 'json',      label: 'JSON' },
          { value: 'form',      label: 'Form Data' },
          { value: 'text',      label: 'Plain Text' },
        ],
        value: 'json',
      },
      { name: 'body', type: 'text', label: '바디 내용', placeholder: '{"key": "value"}' },
    ],
  },
  {
    id: 'get-cookies',
    type: 'get-cookies',
    category: 'api',
    label: '쿠키 가져오기',
    icon: 'cookie',
    color: '#047857',
    fields: [
      { name: 'domain',   type: 'text', label: '도메인 (선택)', placeholder: '.example.com' },
      { name: 'variable', type: 'text', label: '저장 변수명',   placeholder: 'cookies' },
    ],
  },
  {
    id: 'set-cookie',
    type: 'set-cookie',
    category: 'api',
    label: '쿠키 설정',
    icon: 'cookie',
    color: '#047857',
    fields: [
      { name: 'name',  type: 'text', label: '쿠키 이름', placeholder: 'session_id' },
      { name: 'value', type: 'text', label: '쿠키 값',   placeholder: 'abc123' },
      { name: 'domain', type: 'text', label: '도메인',   placeholder: '.example.com' },
    ],
  },
  {
    id: 'save-cookies',
    type: 'save-cookies',
    category: 'api',
    label: '쿠키 파일로 저장',
    icon: 'download',
    color: '#047857',
    fields: [
      { name: 'filepath', type: 'text', label: '저장 경로', placeholder: 'cookies.json' },
    ],
  },
  {
    id: 'load-cookies',
    type: 'load-cookies',
    category: 'api',
    label: '쿠키 파일에서 불러오기',
    icon: 'upload',
    color: '#065f46',
    fields: [
      { name: 'filepath', type: 'text', label: '파일 경로', placeholder: 'cookies.json' },
    ],
  },
  {
    id: 'parse-json',
    type: 'parse-json',
    category: 'api',
    label: 'JSON 파싱',
    icon: 'braces',
    color: '#10b981',
    fields: [
      { name: 'source',   type: 'text', label: '원본 변수',    placeholder: 'response' },
      { name: 'path',     type: 'text', label: 'JSON 경로',    placeholder: 'data.items[0].name' },
      { name: 'variable', type: 'text', label: '저장 변수명',  placeholder: 'itemName' },
    ],
  },
  {
    id: 'api-auth',
    type: 'api-auth',
    category: 'api',
    label: 'API 인증 설정',
    icon: 'key-round',
    color: '#065f46',
    fields: [
      {
        name: 'type',
        type: 'select',
        label: '인증 방식',
        options: [
          { value: 'bearer', label: 'Bearer Token' },
          { value: 'basic',  label: 'Basic Auth' },
          { value: 'apikey', label: 'API Key' },
        ],
        value: 'bearer',
      },
      { name: 'token', type: 'text', label: '토큰 / 키', placeholder: '{{api_key}}' },
    ],
  },

  // ── 데스크톱 (PyAutoGUI) ───────────────────────────────────────────────
  {
    id: 'mouse-click-coords',
    type: 'mouse-click-coords',
    category: 'desktop',
    label: '좌표 클릭 (PyAutoGUI)',
    icon: 'target',
    color: '#ec4899',
    fields: [
      { name: 'x', type: 'number', label: 'X 좌표', placeholder: '100' },
      { name: 'y', type: 'number', label: 'Y 좌표', placeholder: '200' },
      {
        name: 'clicks',
        type: 'select',
        label: '클릭 횟수',
        options: [
          { value: '1', label: '단일 클릭' },
          { value: '2', label: '더블 클릭' },
          { value: '3', label: '트리플 클릭' },
        ],
        value: '1',
      },
    ],
  },
  {
    id: 'mouse-move',
    type: 'mouse-move',
    category: 'desktop',
    label: '마우스 이동',
    icon: 'move',
    color: '#db2777',
    fields: [
      { name: 'x', type: 'number', label: 'X 좌표', placeholder: '500' },
      { name: 'y', type: 'number', label: 'Y 좌표', placeholder: '300' },
      { name: 'duration', type: 'number', label: '이동 시간(초)', placeholder: '0.5' },
    ],
  },
  {
    id: 'pyautogui-type',
    type: 'pyautogui-type',
    category: 'desktop',
    label: '키보드 입력 (PyAutoGUI)',
    icon: 'keyboard',
    color: '#be185d',
    fields: [
      { name: 'text', type: 'text', label: '입력 텍스트', placeholder: '안녕하세요' },
      { name: 'interval', type: 'number', label: '타이핑 간격(초)', placeholder: '0.05' },
    ],
  },
  {
    id: 'pyautogui-hotkey',
    type: 'pyautogui-hotkey',
    category: 'desktop',
    label: '단축키 (PyAutoGUI)',
    icon: 'zap',
    color: '#be185d',
    fields: [
      {
        name: 'hotkey',
        type: 'select',
        label: '단축키',
        options: [
          { value: 'ctrl,c', label: 'Ctrl+C (복사)' },
          { value: 'ctrl,v', label: 'Ctrl+V (붙여넣기)' },
          { value: 'ctrl,a', label: 'Ctrl+A (전체선택)' },
          { value: 'ctrl,s', label: 'Ctrl+S (저장)' },
          { value: 'alt,tab', label: 'Alt+Tab (창전환)' },
          { value: 'alt,f4', label: 'Alt+F4 (닫기)' },
          { value: 'win,d', label: 'Win+D (바탕화면)' },
          { value: 'enter', label: 'Enter' },
          { value: 'esc', label: 'Escape' },
        ],
        value: 'ctrl,v',
      },
    ],
  },
  {
    id: 'image-click',
    type: 'image-click',
    category: 'desktop',
    label: '이미지 찾아 클릭',
    icon: 'image',
    color: '#9d174d',
    fields: [
      { name: 'image_path', type: 'text', label: '이미지 경로', placeholder: 'button.png' },
      { name: 'confidence', type: 'number', label: '정확도 (0-1)', placeholder: '0.9' },
      { name: 'timeout', type: 'number', label: '대기 시간(초)', placeholder: '10' },
    ],
  },
  {
    id: 'clipboard-copy',
    type: 'clipboard-copy',
    category: 'desktop',
    label: '클립보드에 복사',
    icon: 'clipboard-copy',
    color: '#ec4899',
    fields: [
      { name: 'text', type: 'text', label: '복사할 텍스트', placeholder: '{{variable}}' },
    ],
  },
  {
    id: 'clipboard-paste',
    type: 'clipboard-paste',
    category: 'desktop',
    label: '클립보드 붙여넣기',
    icon: 'clipboard-paste',
    color: '#ec4899',
    fields: [
      { name: 'variable', type: 'text', label: '저장할 변수명 (선택)', placeholder: 'clipboard_content' },
    ],
  },
  {
    id: 'window-focus',
    type: 'window-focus',
    category: 'desktop',
    label: '창 활성화',
    icon: 'app-window',
    color: '#db2777',
    fields: [
      { name: 'title', type: 'text', label: '창 제목 (부분 일치)', placeholder: 'Chrome' },
    ],
  },

  // ── 고급 (Advanced) ───────────────────────────────────────────────
  {
    id: 'custom-code',
    type: 'custom-code',
    category: 'advanced',
    label: 'Python 코드 실행',
    icon: 'code',
    color: '#6366f1',
    fields: [
      { name: 'code', type: 'text', label: 'Python 코드', placeholder: 'print("Hello World")' },
      { name: 'description', type: 'text', label: '설명 (선택)', placeholder: '커스텀 로직' },
    ],
  },
  {
    id: 'stealth-mode',
    type: 'stealth-mode',
    category: 'advanced',
    label: '봇 탐지 우회 모드',
    icon: 'shield',
    color: '#4f46e5',
    fields: [
      {
        name: 'mode',
        type: 'select',
        label: '우회 방식',
        options: [
          { value: 'undetected', label: 'Undetected ChromeDriver' },
          { value: 'stealth', label: 'Selenium Stealth' },
          { value: 'debugger', label: '디버거 포트 연결' },
        ],
        value: 'undetected',
      },
      { name: 'debugger_port', type: 'number', label: '디버거 포트 (선택)', placeholder: '9222' },
    ],
  },
  {
    id: 'set-proxy',
    type: 'set-proxy',
    category: 'advanced',
    label: '프록시 설정',
    icon: 'globe-lock',
    color: '#4338ca',
    fields: [
      { name: 'host', type: 'text', label: '프록시 주소', placeholder: '127.0.0.1:8080' },
      { name: 'username', type: 'text', label: '사용자명 (선택)', placeholder: 'user' },
      { name: 'password', type: 'text', label: '비밀번호 (선택)', placeholder: 'pass' },
    ],
  },
  {
    id: 'random-delay',
    type: 'random-delay',
    category: 'advanced',
    label: '랜덤 대기',
    icon: 'shuffle',
    color: '#6366f1',
    fields: [
      { name: 'min', type: 'number', label: '최소 (초)', placeholder: '1' },
      { name: 'max', type: 'number', label: '최대 (초)', placeholder: '5' },
    ],
  },
  {
    id: 'switch-account',
    type: 'switch-account',
    category: 'advanced',
    label: '계정 전환',
    icon: 'user-cog',
    color: '#4f46e5',
    fields: [
      { name: 'account_folder', type: 'text', label: '계정 폴더 경로', placeholder: 'accounts/{{index}}' },
      { name: 'profile_dir', type: 'text', label: '크롬 프로필 경로', placeholder: 'Chrome Data/{{account}}' },
    ],
  },
  {
    id: 'captcha-wait',
    type: 'captcha-wait',
    category: 'advanced',
    label: '캡챠 대기',
    icon: 'puzzle',
    color: '#7c3aed',
    fields: [
      { name: 'timeout', type: 'number', label: '최대 대기(초)', placeholder: '120' },
      {
        name: 'action',
        type: 'select',
        label: '처리 방식',
        options: [
          { value: 'manual', label: '수동 해결 대기' },
          { value: '2captcha', label: '2Captcha API' },
          { value: 'skip', label: '스킵 (발생 시 중단)' },
        ],
        value: 'manual',
      },
    ],
  },
  {
    id: 'db-connect',
    type: 'db-connect',
    category: 'advanced',
    label: 'DB 연결',
    icon: 'database',
    color: '#4338ca',
    fields: [
      {
        name: 'type',
        type: 'select',
        label: 'DB 종류',
        options: [
          { value: 'mysql', label: 'MySQL' },
          { value: 'sqlite', label: 'SQLite' },
          { value: 'postgres', label: 'PostgreSQL' },
        ],
        value: 'mysql',
      },
      { name: 'host', type: 'text', label: '호스트', placeholder: 'localhost' },
      { name: 'database', type: 'text', label: '데이터베이스명', placeholder: 'mydb' },
      { name: 'username', type: 'text', label: '사용자명', placeholder: 'root' },
      { name: 'password', type: 'text', label: '비밀번호', placeholder: '' },
    ],
  },
  {
    id: 'db-query',
    type: 'db-query',
    category: 'advanced',
    label: 'DB 조회',
    icon: 'database',
    color: '#3730a3',
    fields: [
      { name: 'query', type: 'text', label: 'SQL 쿼리', placeholder: 'SELECT * FROM users WHERE id = {{id}}' },
      { name: 'variable', type: 'text', label: '결과 저장 변수', placeholder: 'result' },
    ],
  },
  {
    id: 'db-execute',
    type: 'db-execute',
    category: 'advanced',
    label: 'DB 실행 (INSERT/UPDATE)',
    icon: 'database',
    color: '#3730a3',
    fields: [
      { name: 'query', type: 'text', label: 'SQL 쿼리', placeholder: 'INSERT INTO logs (message) VALUES ({{msg}})' },
    ],
  },
  {
    id: 'read-file',
    type: 'read-file',
    category: 'advanced',
    label: '파일 읽기',
    icon: 'file-text',
    color: '#6366f1',
    fields: [
      { name: 'filepath', type: 'text', label: '파일 경로', placeholder: 'data/input.txt' },
      { name: 'variable', type: 'text', label: '저장 변수명', placeholder: 'file_content' },
      {
        name: 'encoding',
        type: 'select',
        label: '인코딩',
        options: [
          { value: 'utf-8', label: 'UTF-8' },
          { value: 'cp949', label: 'CP949 (한글)' },
          { value: 'euc-kr', label: 'EUC-KR' },
        ],
        value: 'utf-8',
      },
    ],
  },
  {
    id: 'write-file',
    type: 'write-file',
    category: 'advanced',
    label: '파일 쓰기',
    icon: 'file-output',
    color: '#6366f1',
    fields: [
      { name: 'filepath', type: 'text', label: '파일 경로', placeholder: 'output/result.txt' },
      { name: 'content', type: 'text', label: '내용', placeholder: '{{data}}' },
      {
        name: 'mode',
        type: 'select',
        label: '쓰기 모드',
        options: [
          { value: 'overwrite', label: '덮어쓰기' },
          { value: 'append', label: '이어쓰기' },
        ],
        value: 'overwrite',
      },
    ],
  },
  {
    id: 'regex-extract',
    type: 'regex-extract',
    category: 'advanced',
    label: '정규식 추출',
    icon: 'regex',
    color: '#4f46e5',
    fields: [
      { name: 'text', type: 'text', label: '대상 텍스트', placeholder: '{{html}}' },
      { name: 'pattern', type: 'text', label: '정규식 패턴', placeholder: 'price: (\\d+)원' },
      { name: 'variable', type: 'text', label: '저장 변수명', placeholder: 'extracted' },
    ],
  },
  {
    id: 'run-script',
    type: 'run-script',
    category: 'advanced',
    label: '외부 스크립트 실행',
    icon: 'terminal',
    color: '#7c3aed',
    fields: [
      { name: 'command', type: 'text', label: '명령어', placeholder: 'python script.py' },
      { name: 'timeout', type: 'number', label: '타임아웃(초)', placeholder: '60' },
      { name: 'variable', type: 'text', label: '출력 저장 변수', placeholder: 'output' },
    ],
  },
]
