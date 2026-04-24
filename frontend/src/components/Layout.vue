<template>
  <div class="flex min-h-screen bg-gray-100">
    <Sidebar />
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- Top bar -->
      <header class="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shadow-sm">
        <div>
          <h2 class="text-lg font-semibold text-gray-800">{{ pageTitle }}</h2>
          <p class="text-xs text-gray-500 mt-0.5">{{ pageSubtitle }}</p>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-xs text-gray-500">{{ currentDate }}</span>
          <div class="w-2 h-2 rounded-full bg-green-500"></div>
          <span class="text-xs text-gray-500">オンライン</span>
        </div>
      </header>
      <!-- Page content -->
      <div class="flex-1 overflow-y-auto p-6">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './Sidebar.vue'

const route = useRoute()

const pageMeta = {
  '/dashboard': { title: 'ダッシュボード', subtitle: 'コンテンツの概要と統計' },
  '/upload': { title: '動画アップロード', subtitle: 'TikTokへ動画を投稿する' },
  '/settings': { title: '設定', subtitle: 'アカウントとアプリの設定' }
}

const pageTitle = computed(() => pageMeta[route.path]?.title ?? 'TikTok Manager')
const pageSubtitle = computed(() => pageMeta[route.path]?.subtitle ?? '')

const currentDate = computed(() => {
  return new Date().toLocaleDateString('ja-JP', {
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'short'
  })
})
</script>
