import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

export interface Book {
  id: string
  title: string
  node_count: number
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

export interface ProcessingStatus {
  book_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message: string
}

export const booksApi = {
  getBooks: () => api.get<Book[]>('/books'),

  getBook: (bookId: string) => api.get<Book>(`/books/${bookId}`),

  getBookNodes: (bookId: string) => api.get<NarrativeNode[]>(`/books/${bookId}/nodes`),

  getBookStructure: (bookId: string) => api.get('/books/${bookId}/structure'),

  deleteBook: (bookId: string) => api.delete(`/books/${bookId}`),

  uploadBook: (file: File, userId: string = 'default-user') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', userId)
    return api.post<{ book_id: string; status: string; message: string }>('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  getUploadStatus: (bookId: string) => api.get<ProcessingStatus>(`/upload/${bookId}/status`),
}
