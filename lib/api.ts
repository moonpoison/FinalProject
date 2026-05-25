/**
 * AutoFlow API Client
 * 백엔드 API와 통신하기 위한 클라이언트
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Types
export interface UserResponse {
  id: string;
  email: string;
  name: string;
  role: string;
  avatar: string | null;
  joined_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface SignupResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface MarketplaceItemResponse {
  id: string;
  title: string;
  description: string;
  category: string;
  price: number;
  rating: number;
  reviews: number;
  downloads: number;
  creator: string;
  creator_avatar: string | null;
  tags: string[];
  block_colors: string[];
  blocks_data?: any[];  // 블록 데이터 (상세 조회 시)
  features?: string[];  // AI 생성 주요 기능
  usage_steps?: string[];  // AI 생성 사용 방법
  featured: boolean;
  verified: boolean;
  status: string;
  created_at: string;
}

export interface MarketplaceListResponse {
  items: MarketplaceItemResponse[];
  total: number;
}

export interface WorkflowStep {
  id: string;
  label: string;
  description: string;
  block_type: string;
  color: string;
  field_values?: Record<string, any>;
}

export interface WorkflowGroup {
  id: string;
  label: string;
  description: string;
  color: string;
  steps: WorkflowStep[];
}

export interface AIAnalyzeResponse {
  task_name: string;
  summary: string;
  confidence: number;
  groups: WorkflowGroup[];
}

// 대화형 AI 타입
export interface AIQuestion {
  id: string;
  question: string;
  type: "choice" | "text" | "confirm";
  options?: string[];
  default?: string;
}

export interface AIConversationRequest {
  prompt: string;
  answers?: Record<string, string> | null;
  questions?: AIQuestion[] | null;  // 답변 제출 시 질문 내용 포함
}

export interface AIConversationResponse {
  mode: "questions" | "workflow";
  message?: string;
  questions?: AIQuestion[];
  workflow?: any;
  reference_projects?: Array<{
    name: string;
    category: string;
    similarity: number;
    sites: string[];
    libraries: string[];
  }>;
}

export interface BlockData {
  id: string;
  type: string;
  category: string;
  label: string;
  icon: string;
  color: string;
  fields: any[];
  instance_id: string;
  field_values: Record<string, any>;
  group_id?: string;
  group_label?: string;
  group_color?: string;
}

export interface AIGenerateBlocksResponse {
  blocks: BlockData[];
}

// 코드 검증 타입
export interface CodeVerificationIssue {
  severity: "error" | "warning" | "info";
  block_id: string | null;
  message: string;
  suggestion: string | null;
}

export interface CodeVerificationResponse {
  is_valid: boolean;
  score: number;
  summary: string;
  issues: CodeVerificationIssue[];
  test_results: Array<{
    name: string;
    description: string;
    expected_result: string;
    status: "pass" | "fail" | "warning";
  }> | null;
  improved_workflow: any | null;
}

export interface MessageResponse {
  id: string;
  sender_id: string;
  sender_name: string;
  body: string;
  read: boolean;
  created_at: string;
}

export interface ConversationResponse {
  id: string;
  participant_ids: string[];
  participant_names: string[];
  topic: string | null;
  messages: MessageResponse[];
  updated_at: string;
}

export interface PurchaseResponse {
  id: string;
  name: string;
  price: number;
  purchased_at: string;
  creator: string;
  status: string;
  deadline: string | null;
  my_review: { rating: number; text: string } | null;
}

export interface PurchaseListResponse {
  active: PurchaseResponse[];
  pending: PurchaseResponse[];
  cancelled: PurchaseResponse[];
}

export interface TemplateResponse {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  price: number;
  downloads: number;
  revenue: number;
  rating: number;
  reviews: number;
  status: string;
  blocks_data: any[];
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface TemplateListResponse {
  templates: TemplateResponse[];
  total: number;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('auth_token', token);
      } else {
        localStorage.removeItem('auth_token');
      }
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token');
    }
    return null;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let error;
      try {
        error = await response.json();
      } catch {
        error = { detail: 'API 요청 실패' };
      }
      throw new Error(error.detail || 'API 요청 실패');
    }

    return response.json();
  }

  // ─── Auth ───────────────────────────────────────────────────────────────

  async login(email: string, password: string): Promise<LoginResponse> {
    const data = await this.request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async signup(
    email: string,
    password: string,
    name: string,
    role: string = 'buyer'
  ): Promise<SignupResponse> {
    const data = await this.request<SignupResponse>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password, name, role }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async logout(): Promise<void> {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } finally {
      this.setToken(null);
    }
  }

  async getMe(): Promise<UserResponse> {
    return this.request<UserResponse>('/auth/me');
  }

  // ─── Marketplace ────────────────────────────────────────────────────────

  async getMarketplaceItems(params?: {
    category?: string;
    search?: string;
    sort?: string;
    skip?: number;
    limit?: number;
  }): Promise<MarketplaceListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.category && params.category !== '전체') {
      searchParams.set('category', params.category);
    }
    if (params?.search) searchParams.set('search', params.search);
    if (params?.sort) searchParams.set('sort', params.sort);
    if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));

    const query = searchParams.toString();
    return this.request<MarketplaceListResponse>(
      `/marketplace/items${query ? `?${query}` : ''}`
    );
  }

  async getMarketplaceItem(itemId: string): Promise<MarketplaceItemResponse> {
    return this.request<MarketplaceItemResponse>(`/marketplace/items/${itemId}`);
  }

  async createMarketplaceItem(data: {
    title: string;
    description: string;
    category: string;
    price: number;
    tags: string[];
    blocks_data: any[];
    block_colors: string[];
    features?: string[];
    usage_steps?: string[];
  }): Promise<MarketplaceItemResponse> {
    return this.request<MarketplaceItemResponse>('/marketplace/items', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateMarketplaceItem(
    itemId: string,
    data: Partial<{
      title: string;
      description: string;
      category: string;
      price: number;
      tags: string[];
      status: string;
    }>
  ): Promise<MarketplaceItemResponse> {
    return this.request<MarketplaceItemResponse>(`/marketplace/items/${itemId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteMarketplaceItem(itemId: string): Promise<void> {
    await this.request(`/marketplace/items/${itemId}`, { method: 'DELETE' });
  }

  // ─── Purchases ──────────────────────────────────────────────────────────

  async getPurchases(): Promise<PurchaseListResponse> {
    return this.request<PurchaseListResponse>('/purchases');
  }

  async purchaseItem(itemId: string): Promise<PurchaseResponse> {
    return this.request<PurchaseResponse>('/purchases', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId }),
    });
  }

  async confirmPurchase(purchaseId: string): Promise<PurchaseResponse> {
    return this.request<PurchaseResponse>(`/purchases/${purchaseId}/confirm`, {
      method: 'POST',
    });
  }

  async cancelPurchase(purchaseId: string): Promise<PurchaseResponse> {
    return this.request<PurchaseResponse>(`/purchases/${purchaseId}/cancel`, {
      method: 'POST',
    });
  }

  // PortOne 결제 검증
  async verifyPayment(paymentId: string, itemId: string, amount: number): Promise<PurchaseResponse> {
    return this.request<PurchaseResponse>('/purchases/verify-payment', {
      method: 'POST',
      body: JSON.stringify({ payment_id: paymentId, item_id: itemId, amount }),
    });
  }

  // ─── Chat ───────────────────────────────────────────────────────────────

  async getConversations(): Promise<ConversationResponse[]> {
    return this.request<ConversationResponse[]>('/conversations');
  }

  async startConversation(
    otherName: string,
    topic: string
  ): Promise<ConversationResponse> {
    return this.request<ConversationResponse>('/conversations', {
      method: 'POST',
      body: JSON.stringify({ other_name: otherName, topic }),
    });
  }

  async sendMessage(
    conversationId: string,
    body: string
  ): Promise<MessageResponse> {
    return this.request<MessageResponse>(
      `/conversations/${conversationId}/messages`,
      {
        method: 'POST',
        body: JSON.stringify({ body }),
      }
    );
  }

  async markMessagesRead(conversationId: string): Promise<void> {
    await this.request(`/conversations/${conversationId}/read`, {
      method: 'POST',
    });
  }

  async getUnreadCount(): Promise<{ count: number }> {
    return this.request<{ count: number }>('/conversations/unread-count');
  }

  // ─── Users ──────────────────────────────────────────────────────────────

  async updateProfile(data: {
    name?: string;
    avatar?: string;
    role?: string;
    notif_email?: boolean;
    notif_sale?: boolean;
    notif_review?: boolean;
  }): Promise<UserResponse> {
    return this.request<UserResponse>('/users/me', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getMyTemplates(): Promise<TemplateListResponse> {
    return this.request<TemplateListResponse>('/users/me/templates');
  }

  async createTemplate(data: {
    name: string;
    description?: string;
    category?: string;
    price: number;
    tags: string[];
    blocks_data: any[];
  }): Promise<TemplateResponse> {
    return this.request<TemplateResponse>('/users/me/templates', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTemplate(
    templateId: string,
    data: Partial<{
      name: string;
      description: string;
      category: string;
      price: number;
      tags: string[];
      status: string;
    }>
  ): Promise<TemplateResponse> {
    return this.request<TemplateResponse>(`/users/me/templates/${templateId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteTemplate(templateId: string): Promise<void> {
    await this.request(`/users/me/templates/${templateId}`, { method: 'DELETE' });
  }

  async getMyStats(): Promise<{
    templates_count: number;
    total_downloads: number;
    total_revenue: number;
    avg_rating: number;
    active_purchases: number;
  }> {
    return this.request('/users/me/stats');
  }

  // ─── AI ─────────────────────────────────────────────────────────────────

  async analyzePrompt(prompt: string): Promise<AIAnalyzeResponse> {
    return this.request<AIAnalyzeResponse>('/ai/analyze', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    });
  }

  /**
   * Stream analyze prompt with real-time workflow generation
   */
  analyzePromptStream(
    prompt: string,
    onInfo: (info: { task_name: string; summary: string; confidence: number; total_groups: number }) => void,
    onGroup: (index: number, group: WorkflowGroup) => void,
    onDone: () => void,
    onError: (error: Error) => void
  ): () => void {
    const token = this.getToken();
    const controller = new AbortController();

    const fetchStream = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/ai/analyze-stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ prompt }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error('Stream request failed');
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No reader available');
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === 'info') {
                  onInfo({
                    task_name: data.task_name,
                    summary: data.summary,
                    confidence: data.confidence,
                    total_groups: data.total_groups,
                  });
                } else if (data.type === 'group') {
                  onGroup(data.index, data.group);
                } else if (data.type === 'done') {
                  onDone();
                }
              } catch {
                // Ignore parse errors
              }
            }
          }
        }
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          onError(error);
        }
      }
    };

    fetchStream();

    // Return cleanup function
    return () => controller.abort();
  }

  async generateBlocks(groups: WorkflowGroup[]): Promise<AIGenerateBlocksResponse> {
    return this.request<AIGenerateBlocksResponse>('/ai/generate-blocks', {
      method: 'POST',
      body: JSON.stringify({ groups }),
    });
  }

  /**
   * 대화형 AI 분석 - 질문 후 워크플로우 생성
   */
  async conversationAnalyze(request: AIConversationRequest): Promise<AIConversationResponse> {
    return this.request<AIConversationResponse>('/ai/conversation', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * 블록 구성 분석하여 마켓플레이스용 개요 생성
   */
  async analyzeBlocksForDescription(blocks: any[], title: string): Promise<{
    description: string;
    features: string[];
    usage_steps: string[];
  }> {
    return this.request<{ description: string; features: string[]; usage_steps: string[] }>('/ai/analyze-blocks', {
      method: 'POST',
      body: JSON.stringify({ blocks, title }),
    });
  }

  /**
   * AI 생성 코드 2차 검증
   */
  async verifyCode(workflow: any, originalPrompt: string): Promise<CodeVerificationResponse> {
    return this.request<CodeVerificationResponse>('/ai/verify-code', {
      method: 'POST',
      body: JSON.stringify({ workflow, original_prompt: originalPrompt }),
    });
  }

  // ─── Reviews ────────────────────────────────────────────────────────────

  async getItemReviews(itemId: string): Promise<
    Array<{
      id: string;
      user_id: string;
      user_name: string;
      rating: number;
      text: string;
      created_at: string;
    }>
  > {
    return this.request(`/marketplace/items/${itemId}/reviews`);
  }

  async createReview(
    itemId: string,
    data: { rating: number; text: string }
  ): Promise<{
    id: string;
    user_id: string;
    user_name: string;
    rating: number;
    text: string;
    created_at: string;
  }> {
    return this.request(`/marketplace/items/${itemId}/reviews`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ─── Workspaces ──────────────────────────────────────────────────────────

  async getWorkspaces(): Promise<WorkspaceListResponse> {
    return this.request<WorkspaceListResponse>('/workspaces');
  }

  async createWorkspace(data: {
    name?: string;
    description?: string;
    blocks_data?: any[];
  }): Promise<WorkspaceResponse> {
    return this.request<WorkspaceResponse>('/workspaces', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getWorkspace(workspaceId: string): Promise<WorkspaceResponse> {
    return this.request<WorkspaceResponse>(`/workspaces/${workspaceId}`);
  }

  async updateWorkspace(
    workspaceId: string,
    data: {
      name?: string;
      description?: string;
      blocks_data?: any[];
      order_index?: number;
      is_active?: boolean;
    }
  ): Promise<WorkspaceResponse> {
    return this.request<WorkspaceResponse>(`/workspaces/${workspaceId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteWorkspace(workspaceId: string): Promise<void> {
    await this.request(`/workspaces/${workspaceId}`, { method: 'DELETE' });
  }

  async saveWorkspaceBlocks(workspaceId: string, blocks: any[]): Promise<WorkspaceResponse> {
    return this.request<WorkspaceResponse>(`/workspaces/${workspaceId}/blocks`, {
      method: 'POST',
      body: JSON.stringify(blocks),
    });
  }

  async bulkUpdateWorkspaces(updates: { id: string; order_index?: number; name?: string }[]): Promise<void> {
    await this.request('/workspaces/bulk-update', {
      method: 'POST',
      body: JSON.stringify({ updates }),
    });
  }

  async createWorkspaceFromPurchase(itemId: string, name: string): Promise<WorkspaceResponse> {
    return this.request<WorkspaceResponse>(`/workspaces/from-purchase?item_id=${itemId}&name=${encodeURIComponent(name)}`, {
      method: 'POST',
    });
  }

  // ─── Videos ─────────────────────────────────────────────────────────────

  async uploadVideo(file: File): Promise<VideoUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const token = this.getToken();
    const headers: HeadersInit = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}/videos/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '영상 업로드 실패' }));
      throw new Error(error.detail || '영상 업로드 실패');
    }

    return response.json();
  }

  async getVideos(): Promise<VideoListResponse> {
    return this.request<VideoListResponse>('/videos');
  }

  async getVideo(videoId: string): Promise<VideoDetailResponse> {
    return this.request<VideoDetailResponse>(`/videos/${videoId}`);
  }

  async getVideoStatus(videoId: string): Promise<VideoStatusResponse> {
    return this.request<VideoStatusResponse>(`/videos/${videoId}/status`);
  }

  async deleteVideo(videoId: string): Promise<void> {
    await this.request(`/videos/${videoId}`, { method: 'DELETE' });
  }

  async applyVideoBlocks(videoId: string, workspaceName: string): Promise<{
    message: string;
    workspace_id: string;
    block_count: number;
  }> {
    return this.request(`/videos/${videoId}/apply-blocks?workspace_name=${encodeURIComponent(workspaceName)}`, {
      method: 'POST',
    });
  }

  // ─── Account ─────────────────────────────────────────────────────────────

  async deleteAccount(): Promise<void> {
    await this.request('/users/me', { method: 'DELETE' });
    this.setToken(null);
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.request('/users/me/password', {
      method: 'PUT',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  }

  // ─── Execution ─────────────────────────────────────────────────────────────

  async generateCode(blocks: any[], workflowName: string = "automation", prompt?: string): Promise<GenerateCodeResponse> {
    return this.request<GenerateCodeResponse>('/execution/generate-code', {
      method: 'POST',
      body: JSON.stringify({ blocks, workflow_name: workflowName, prompt }),
    });
  }

  async queueExecution(blocks: any[], workflowName: string = "automation"): Promise<QueueExecutionResponse> {
    return this.request<QueueExecutionResponse>('/execution/queue-execution', {
      method: 'POST',
      body: JSON.stringify({ blocks, workflow_name: workflowName }),
    });
  }

  async getExecutionStatus(commandId: string): Promise<ExecutionStatusResponse> {
    return this.request<ExecutionStatusResponse>(`/execution/execution-status/${commandId}`);
  }

  async stopExecution(commandId: string): Promise<{ success: boolean; message: string; status: string }> {
    return this.request(`/execution/stop-execution/${commandId}`, {
      method: 'POST',
    });
  }

  // ─── Agent ─────────────────────────────────────────────────────────────────

  async getAgentVersion(): Promise<{ version: string; downloads: Record<string, string> }> {
    return this.request('/execution/agent/version');
  }

  async generateAgentToken(): Promise<{ token: string; expires_in_days: number; message: string }> {
    return this.request('/auth/agent-token', { method: 'POST' });
  }

  getAgentDownloadUrl(platform: string): string {
    return `${API_BASE_URL}/execution/agent/download?platform=${platform}`;
  }

  // ─── Knowledge Base ─────────────────────────────────────────────────────────

  async getKnowledgeBaseStats(): Promise<KnowledgeBaseStats> {
    return this.request<KnowledgeBaseStats>('/knowledge/stats');
  }

  async searchKnowledgeBase(query: string, topK: number = 5): Promise<KnowledgeSearchResponse> {
    return this.request<KnowledgeSearchResponse>('/knowledge/search', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    });
  }

  async getKnowledgeContext(prompt: string, topK: number = 3): Promise<KnowledgeContextResponse> {
    return this.request<KnowledgeContextResponse>('/knowledge/context', {
      method: 'POST',
      body: JSON.stringify({ prompt, top_k: topK }),
    });
  }

  async getKnowledgeProject(projectId: string): Promise<KnowledgeProject> {
    return this.request<KnowledgeProject>(`/knowledge/project/${projectId}`);
  }

  async getKnowledgeCategories(): Promise<KnowledgeCategoriesResponse> {
    return this.request<KnowledgeCategoriesResponse>('/knowledge/categories');
  }

  async getSiteSelectors(site: string): Promise<SiteSelectorsResponse> {
    return this.request<SiteSelectorsResponse>(`/knowledge/selectors/${site}`);
  }

  async buildKnowledgeIndex(force: boolean = false): Promise<{ success: boolean; message: string }> {
    return this.request('/knowledge/build', {
      method: 'POST',
      body: JSON.stringify({ force }),
    });
  }

  // ─── Selector Validation ─────────────────────────────────────────────────────

  /**
   * 셀렉터 검증 - 여러 CSS/XPath 셀렉터가 실제 페이지에 존재하는지 확인
   */
  async validateSelectors(url: string, selectors: SelectorInput[]): Promise<SelectorValidationResponse> {
    return this.request<SelectorValidationResponse>('/validation/selectors', {
      method: 'POST',
      body: JSON.stringify({ url, selectors }),
    });
  }

  /**
   * 워크플로우 검증 - 블록들의 모든 셀렉터를 한번에 검증
   */
  async validateWorkflow(url: string, blocks: any[]): Promise<WorkflowValidationResponse> {
    return this.request<WorkflowValidationResponse>('/validation/workflow', {
      method: 'POST',
      body: JSON.stringify({ url, blocks }),
    });
  }

  /**
   * 페이지 분석 - 자동화에 유용한 요소들 추출 (폼, 입력창, 버튼 등)
   */
  async analyzePage(url: string): Promise<PageAnalysisResponse> {
    return this.request<PageAnalysisResponse>('/validation/analyze-page', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }

  /**
   * 셀렉터 추천 - 특정 액션에 적합한 셀렉터 자동 추천
   */
  async suggestSelectors(url: string, actionType: string, context?: string): Promise<SelectorSuggestionsResponse> {
    return this.request<SelectorSuggestionsResponse>('/validation/suggest-selectors', {
      method: 'POST',
      body: JSON.stringify({ url, action_type: actionType, context }),
    });
  }
}

// Execution Types
export interface GenerateCodeResponse {
  success: boolean;
  code: string;
  block_count: number;
}

export interface QueueExecutionResponse {
  success: boolean;
  command_id: string;
  message: string;
}

export interface ExecutionStatusResponse {
  command_id: string;
  status?: string;
  success?: boolean;
  data?: any;
  error?: string;
  message?: string;
}

// Video Types
export interface VideoUploadResponse {
  id: string;
  filename: string;
  status: string;
  message: string;
}

export interface VideoStatusResponse {
  id: string;
  filename: string;
  original_filename: string;
  status: string;
  progress: number;
  error_message: string | null;
  duration: number | null;
  frame_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface VideoDetailResponse extends VideoStatusResponse {
  transcript: string | null;
  analysis_result: {
    task_name: string;
    summary: string;
    confidence: number;
    // 영상 분석에서 생성된 프롬프트
    generated_prompt?: string;
    task_summary?: string;
    detected_site?: string;
    detected_url?: string;
    detected_actions: string[] | Array<{
      step: number;
      action: string;
      element: string;
      url_or_app: string;
      screenshot_index: number;
    }>;
    detected_elements?: string[];
    groups?: WorkflowGroup[];
  } | null;
  generated_blocks: BlockData[] | null;
}

export interface VideoListResponse {
  videos: VideoStatusResponse[];
  total: number;
}

// Workspace Types
export interface WorkspaceResponse {
  id: string;
  name: string;
  description: string | null;
  blocks_data: any[];
  order_index: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceListResponse {
  workspaces: WorkspaceResponse[];
  total: number;
}

// Knowledge Base Types
export interface KnowledgeBaseStats {
  total_projects: number;
  total_lines: number;
  categories: Record<string, number>;
  has_vector_db: boolean;
}

export interface KnowledgeSearchResult {
  id: string;
  name: string;
  category: string;
  subcategory: string;
  sites: string[];
  libraries: string[];
  description: string;
  score: number;
  keyword_score: number;
  semantic_score: number;
}

export interface KnowledgeSearchResponse {
  success: boolean;
  count: number;
  results: KnowledgeSearchResult[];
}

export interface KnowledgeContextResponse {
  found: boolean;
  count: number;
  context: string;
  references: Array<{
    name: string;
    category: string;
    subcategory: string;
    sites: string[];
    libraries: string[];
    actions: string[];
    selectors: string[];
    description: string;
    similarity: number;
    code_sample: string;
  }>;
}

export interface KnowledgeProject {
  id: string;
  name: string;
  category: string;
  subcategory: string;
  sites: string[];
  libraries: string[];
  actions: string[];
  selectors: string[];
  description: string;
  main_code: string;
  file_count: number;
  total_lines: number;
}

export interface KnowledgeCategoriesResponse {
  total: number;
  categories: Array<{
    name: string;
    count: number;
  }>;
}

export interface SiteSelectorsResponse {
  site: string;
  count: number;
  selectors: string[];
}

// Selector Validation Types
export interface SelectorInput {
  selector: string;
  type: 'css' | 'xpath';
  name?: string;
}

export interface SelectorValidationResult {
  name?: string;
  selector: string;
  selector_type: string;
  is_valid: boolean;
  match_count: number;
  sample_text?: string;
  confidence: number;
  alternatives: string[];
  error?: string;
}

export interface SelectorValidationResponse {
  url: string;
  fetch_success: boolean;
  js_required: boolean;
  html_length?: number;
  error?: string;
  validations: SelectorValidationResult[];
  summary: {
    valid: number;
    invalid: number;
    total: number;
  };
}

export interface WorkflowValidationResponse {
  url: string;
  fetch_success: boolean;
  js_required: boolean;
  error?: string;
  blocks: Array<SelectorValidationResult & {
    block_id: string;
    block_type: string;
    label: string;
  }>;
  summary: {
    valid: number;
    invalid: number;
    total: number;
  };
}

export interface PageElement {
  id?: string;
  name?: string;
  type?: string;
  text?: string;
  placeholder?: string;
  selector: string;
  href?: string;
  action?: string;
  method?: string;
}

export interface PageListElement {
  container_selector: string;
  item_count: number;
  item_selector: string;
  sample_text?: string;
}

export interface PageAnalysisResponse {
  success: boolean;
  url: string;
  title?: string;
  html_length?: number;
  error?: string;
  elements?: {
    forms: PageElement[];
    inputs: PageElement[];
    buttons: PageElement[];
    lists: PageListElement[];
    links: PageElement[];
  };
}

export interface SelectorSuggestion {
  selector: string;
  confidence: number;
  description: string;
}

export interface SelectorSuggestionsResponse {
  success: boolean;
  url: string;
  action_type: string;
  suggestions: SelectorSuggestion[];
}

export const api = new ApiClient();
