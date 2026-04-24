import { ref } from 'vue'

export function useApiWithRefresh() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const needsTiktokReconnect = ref(false)

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

  return { callWithRefresh, needsTiktokReconnect, baseUrl }
}
