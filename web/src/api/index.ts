import axios, { type AxiosInstance } from 'axios'

// === Types ===

export interface Book {
  id: string
  user_id: string
  title: string
  author?: string
  publisher?: string
  cover_url?: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  nodes_file_path: string
  created_at: string
}

export interface User {
  id: string
  username: string
  email: string
  profile: Record<string, unknown>
  created_at: string
}

export interface CharacterState {
  name: string
  state_before: string
}

export interface RelationshipStateChange {
  pair: string
  from_state: string
  to_state: string
}

export interface NarrativeNode {
  id: string
  parent_chunk_id: string
  beat_index: number
  scene: string
  location: string
  scene_timing: string
  characters: CharacterState[]
  situation: string
  turning_point: string
  emotional_arc: string
  mood_tone: string
  narrative_rhythm: string
  discussion_prompts: string[]
  relationship_delta: RelationshipStateChange[]
  prev_node_id: string
  narrative_role: string
  timeline_order: number
  timeline_anchor: string
  is_time_jump: boolean
  jump_direction: string
  jump_label: string
  thread_id: string
  thread_name: string
  thread_prev_node_id: string
  thread_next_node_id: string
  branch_from_node: string
  converges_to_node: string
  is_convergence: boolean
}

export interface StoryStructure {
  title: string
  genre: string
  target_audience: string
  themes: string[]
  arcs: Array<{
    name: string
    type: string
    description: string
  }>
}

export interface NodesResponse {
  book_id: string
  structure: StoryStructure | null
  nodes: NarrativeNode[]
}

export interface ProcessingStatus {
  book_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message: string
}

export interface AuthToken {
  access_token: string
  token_type: string
}

// === API Client ===

function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: '/api',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  // Add auth token to requests
  client.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  // Handle auth errors
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }
      return Promise.reject(error)
    }
  )

  return client
}

export const api = createApiClient()

// === API Methods ===

export const authApi = {
  register: (username: string, email: string, password: string) =>
    api.post<AuthToken>('/auth/register', { username, email, password }),

  login: (username: string, password: string) =>
    api.post<AuthToken>('/auth/login', { username, password }),
}

export const userApi = {
  getMe: () => api.get<User>('/users/me'),

  updateMe: (profile: Record<string, unknown>) =>
    api.patch<User>('/users/me', profile),
}

export const booksApi = {
  getBooks: () => api.get<Book[]>('/books'),

  getBook: (bookId: string) => api.get<Book>(`/books/${bookId}`),

  createBook: (title: string) =>
    api.post<Book>('/books', { title }),

  deleteBook: (bookId: string) =>
    api.delete(`/books/${bookId}`),

  getBookNodes: (bookId: string) =>
    api.get<NodesResponse>(`/books/${bookId}/nodes`),

  saveBookNodes: (bookId: string, nodes: NarrativeNode[], structure?: StoryStructure) =>
    api.post(`/books/${bookId}/nodes`, { nodes, structure }),

  uploadBook: (file: File, meta?: { title?: string; author?: string; publisher?: string }) => {
    const formData = new FormData()
    formData.append('file', file)
    if (meta?.title) formData.append('title', meta.title)
    if (meta?.author) formData.append('author', meta.author)
    if (meta?.publisher) formData.append('publisher', meta.publisher)
    return api.post<Book>('/books/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
