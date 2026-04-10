import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { booksApi, type Book, type NarrativeNode } from '../api'

export const useBooksStore = defineStore('books', () => {
  const books = ref<Book[]>([])
  const currentBook = ref<Book | null>(null)
  const nodes = ref<NarrativeNode[]>([])
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
    // Sort each thread by timeline_order
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
    } catch (e) {
      error.value = 'Failed to fetch books'
    } finally {
      loading.value = false
    }
  }

  async function fetchBookNodes(bookId: string) {
    loading.value = true
    error.value = null
    try {
      const [bookRes, nodesRes] = await Promise.all([
        booksApi.getBook(bookId),
        booksApi.getBookNodes(bookId),
      ])
      currentBook.value = bookRes.data
      nodes.value = nodesRes.data
    } catch (e) {
      error.value = 'Failed to fetch book details'
    } finally {
      loading.value = false
    }
  }

  async function uploadBook(file: File) {
    const res = await booksApi.uploadBook(file)
    return res.data.book_id
  }

  function clearCurrentBook() {
    currentBook.value = null
    nodes.value = []
  }

  return {
    books,
    currentBook,
    nodes,
    loading,
    error,
    nodesByThread,
    threadIds,
    fetchBooks,
    fetchBookNodes,
    uploadBook,
    clearCurrentBook,
  }
})