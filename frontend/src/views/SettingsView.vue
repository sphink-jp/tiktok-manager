<template>
  <Layout>
    <div class="max-w-2xl mx-auto space-y-6">
      <!-- TikTok連携カード -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="px-6 py-5 border-b border-gray-100">
          <h3 class="font-semibold text-gray-800 text-lg">TikTok連携</h3>
          <p class="text-sm text-gray-500 mt-1">TikTokアカウントと連携することで動画の投稿・一覧取得が可能になります</p>
        </div>
        <div class="px-6 py-6">
          <div v-if="user && user.auth_provider === 'tiktok'" class="flex items-center gap-4">
            <img
              v-if="user.avatar_url"
              :src="user.avatar_url"
              :alt="user.display_name"
              class="w-12 h-12 rounded-full object-cover"
            />
            <div v-else class="w-12 h-12 rounded-full bg-pink-600 flex items-center justify-center text-white text-lg font-bold">
              {{ (user.display_name || '?').charAt(0).toUpperCase() }}
            </div>
            <div>
              <p class="font-medium text-gray-800">{{ user.display_name }}</p>
              <p class="text-sm text-green-600 flex items-center gap-1">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                TikTok連携済み
              </p>
            </div>
          </div>
          <div v-else-if="user && user.auth_provider === 'google'" class="space-y-4">
            <p class="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
              現在Googleアカウントでログイン中です。動画の投稿・一覧取得にはTikTokアカウントとの連携が必要です。
            </p>
            <a
              :href="tiktokLoginUrl"
              class="inline-flex items-center gap-3 bg-black hover:bg-gray-900 text-white font-semibold py-3 px-6 rounded-xl transition-colors"
            >
              <svg viewBox="0 0 24 24" class="w-5 h-5 fill-current">
                <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.28 8.28 0 004.84 1.54V6.79a4.85 4.85 0 01-1.07-.1z"/>
              </svg>
              TikTokと連携する
            </a>
          </div>
          <div v-else class="text-sm text-gray-400">読み込み中...</div>
        </div>
      </div>

      <!-- アカウント情報カード -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="px-6 py-5 border-b border-gray-100">
          <h3 class="font-semibold text-gray-800 text-lg">アカウント情報</h3>
        </div>
        <div class="px-6 py-6">
          <div v-if="user" class="space-y-3">
            <div class="flex items-center gap-2">
              <span class="text-sm text-gray-500 w-32">ログイン方法</span>
              <span class="text-sm font-medium text-gray-800 capitalize">{{ user.auth_provider }}</span>
            </div>
            <div v-if="user.email" class="flex items-center gap-2">
              <span class="text-sm text-gray-500 w-32">メールアドレス</span>
              <span class="text-sm font-medium text-gray-800">{{ user.email }}</span>
            </div>
            <div v-if="user.name" class="flex items-center gap-2">
              <span class="text-sm text-gray-500 w-32">表示名</span>
              <span class="text-sm font-medium text-gray-800">{{ user.name }}</span>
            </div>
            <div v-if="user.display_name" class="flex items-center gap-2">
              <span class="text-sm text-gray-500 w-32">TikTok名</span>
              <span class="text-sm font-medium text-gray-800">{{ user.display_name }}</span>
            </div>
          </div>
          <div v-else class="text-sm text-gray-400">読み込み中...</div>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Layout from '../components/Layout.vue'

const user = ref(null)
const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
const tiktokLoginUrl = computed(() => `${baseUrl}/auth/tiktok`)

async function fetchUser() {
  try {
    const res = await fetch(`${baseUrl}/auth/me`, { credentials: 'include' })
    if (res.ok) {
      user.value = await res.json()
    }
  } catch {
    // ignore
  }
}

onMounted(fetchUser)
</script>
