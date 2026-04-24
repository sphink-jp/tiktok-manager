<template>
  <Layout>
    <!-- Error banner -->
    <div v-if="error" class="mb-6 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
      {{ error }}
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
      <div
        v-for="stat in stats"
        :key="stat.label"
        class="bg-white rounded-xl p-5 shadow-sm border border-gray-100 flex items-center gap-4 hover:shadow-md transition-shadow"
      >
        <div class="flex items-center justify-center w-12 h-12 rounded-xl flex-shrink-0" :class="stat.bgColor">
          <component :is="stat.icon" class="w-6 h-6" :class="stat.iconColor" />
        </div>
        <div>
          <p class="text-xs text-gray-500 font-medium uppercase tracking-wide">{{ stat.label }}</p>
          <p v-if="loading" class="text-2xl font-bold text-gray-300 mt-0.5 animate-pulse">---</p>
          <p v-else class="text-2xl font-bold text-gray-800 mt-0.5">{{ stat.value }}</p>
        </div>
      </div>
    </div>

    <!-- Recent Uploads Table -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <h3 class="font-semibold text-gray-800">最近のアップロード</h3>
        <router-link to="/upload" class="text-sm text-pink-600 hover:text-pink-700 font-medium">
          新規アップロード →
        </router-link>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="px-6 py-8 text-center text-gray-400 text-sm animate-pulse">
        動画データを読み込み中...
      </div>

      <!-- Empty state -->
      <div v-else-if="!loading && videos.length === 0" class="px-6 py-8 text-center text-gray-400 text-sm">
        動画がありません。最初の動画をアップロードしましょう。
      </div>

      <!-- Table -->
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50">
            <tr>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">タイトル</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">投稿日時</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">ビュー数</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">いいね</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="video in videos" :key="video.id" class="hover:bg-gray-50 transition-colors">
              <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                  <img
                    v-if="video.cover_image_url"
                    :src="video.cover_image_url"
                    alt="cover"
                    class="w-10 h-10 rounded-lg object-cover flex-shrink-0"
                  />
                  <div v-else class="w-10 h-10 rounded-lg bg-gradient-to-br from-pink-400 to-purple-500 flex-shrink-0"></div>
                  <span class="font-medium text-gray-800 truncate max-w-[200px]">{{ video.title || '(タイトルなし)' }}</span>
                </div>
              </td>
              <td class="px-6 py-4 text-gray-500">{{ formatDate(video.create_time) }}</td>
              <td class="px-6 py-4 text-gray-700 font-medium">{{ formatNumber(video.view_count) }}</td>
              <td class="px-6 py-4 text-gray-700 font-medium">{{ formatNumber(video.like_count) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { defineComponent, h, ref, computed, onMounted } from 'vue'
import Layout from '../components/Layout.vue'

// ── Icon components ──────────────────────────────────────────────────────────
const VideoIcon = defineComponent({
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z' })
  ])
})

const EyeIcon = defineComponent({
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' }),
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z' })
  ])
})

const HeartIcon = defineComponent({
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z' })
  ])
})

const TrendIcon = defineComponent({
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' })
  ])
})

// ── State ────────────────────────────────────────────────────────────────────
const videos = ref([])
const loading = ref(true)
const error = ref('')

// ── Computed stats from real API data ────────────────────────────────────────
const totalVideos = computed(() => videos.value.length)
const totalViews = computed(() =>
  videos.value.reduce((sum, v) => sum + (v.view_count ?? 0), 0)
)
const totalLikes = computed(() =>
  videos.value.reduce((sum, v) => sum + (v.like_count ?? 0), 0)
)

const stats = computed(() => [
  {
    label: '取得動画数',
    value: String(totalVideos.value),
    icon: VideoIcon,
    bgColor: 'bg-pink-50',
    iconColor: 'text-pink-500',
  },
  {
    label: '合計ビュー数',
    value: formatNumber(totalViews.value),
    icon: EyeIcon,
    bgColor: 'bg-blue-50',
    iconColor: 'text-blue-500',
  },
  {
    label: 'いいね合計',
    value: formatNumber(totalLikes.value),
    icon: HeartIcon,
    bgColor: 'bg-red-50',
    iconColor: 'text-red-500',
  },
  {
    label: '取得件数上限',
    value: '20',
    icon: TrendIcon,
    bgColor: 'bg-green-50',
    iconColor: 'text-green-500',
  },
])

// ── Helpers ──────────────────────────────────────────────────────────────────
function formatNumber(n) {
  if (n == null) return '-'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function formatDate(unixSeconds) {
  if (!unixSeconds) return '-'
  return new Date(unixSeconds * 1000).toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ── Data fetch ───────────────────────────────────────────────────────────────
async function fetchVideos() {
  loading.value = true
  error.value = ''

  try {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    const res = await fetch(`${baseUrl}/api/videos`, { credentials: 'include' })

    if (res.status === 401) {
      error.value = 'TikTok認証が必要です。サイドバーのTikTokログインボタンから連携してください。'
      return
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      error.value = body.detail ?? '動画一覧の取得に失敗しました'
      return
    }

    const json = await res.json()
    videos.value = json?.data?.videos ?? []
  } catch {
    error.value = 'ネットワークエラーが発生しました'
  } finally {
    loading.value = false
  }
}

onMounted(fetchVideos)
</script>
