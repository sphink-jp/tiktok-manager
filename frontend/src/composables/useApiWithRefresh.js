import { ref } from 'vue'

export function useApiWithRefresh() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const needsTiktokReconnect = ref(false)

  async function checkHasTiktok() {
    try {
      const res = await fetch(`${baseUrl}/auth/me`, { credentials: 'include' })
      if (res.ok) {
        const data = await res.json()
        if (!data.has_tiktok) {
          needsTiktokReconnect.value = true
        }
      }
    } catch {
      // ignore network errors — dashboard will handle via fetchVideos
    }
  }

  async function callWithRefresh(fetchFn) {
    const res = await fetchFn()
    if (res.status !== 401) return res

    const refreshRes = await fetch(`${baseUrl}/auth/tiktok/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
    if (!refreshRes.ok) {
      needsTiktokReconnect.value = true
      return res
    }

    return fetchFn()
  }

  return { callWithRefresh, needsTiktokReconnect, baseUrl, checkHasTiktok }
}
