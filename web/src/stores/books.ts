import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { booksApi, type Book, type NarrativeNode, type NodesResponse } from '../api'

export const useBooksStore = defineStore('books', () => {
  const books = ref<Book[]>([])
  const currentBook = ref<Book | null>(null)
  const nodes = ref<NarrativeNode[]>([])
  const structure = ref<NodesResponse['structure']>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const nodesByThread = computed(() => {
    const grouped: Record<string, NarrativeNode[]> = {}
    for (const node of nodes.value) {
      const threadId = node.thread_id || 'main'
      if (!grouped[threadId]) {
        grouped[threadId] = []
      }
      grouped[threadId].push(node)
    }
    for (const threadId in grouped) {
      grouped[threadId].sort((a, b) => a.timeline_order - b.timeline_order)
    }
    return grouped
  })

  const threadIds = computed(() => Object.keys(nodesByThread.value))

  async function fetchBooks() {
    loading.value = true
    error.value = null
    try {
      const res = await booksApi.getBooks()
      books.value = res.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || '获取书籍列表失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchBookNodes(bookId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await booksApi.getBookNodes(bookId)
      currentBook.value = { id: bookId } as Book
      nodes.value = res.data.nodes || []
      structure.value = res.data.structure || null
    } catch (e: any) {
      error.value = e.response?.data?.detail || '获取书籍详情失败'
    } finally {
      loading.value = false
    }
  }

  async function createBook(title: string) {
    loading.value = true
    error.value = null
    try {
      const res = await booksApi.createBook(title)
      books.value.unshift(res.data)
      return res.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || '创建书籍失败'
      return null
    } finally {
      loading.value = false
    }
  }

  async function deleteBook(bookId: string) {
    try {
      await booksApi.deleteBook(bookId)
      books.value = books.value.filter(b => b.id !== bookId)
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || '删除书籍失败'
      return false
    }
  }

  function clearCurrentBook() {
    currentBook.value = null
    nodes.value = []
    structure.value = null
  }

  return {
    books,
    currentBook,
    nodes,
    structure,
    loading,
    error,
    nodesByThread,
    threadIds,
    fetchBooks,
    fetchBookNodes,
    createBook,
    deleteBook,
    clearCurrentBook,
  }
})
