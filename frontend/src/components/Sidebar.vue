<template>
  <aside
    class="flex flex-col w-64 min-h-screen bg-gray-900 border-r border-gray-800 shadow-xl"
    :class="{ 'w-16': collapsed }"
  >
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-5 border-b border-gray-800">
      <div v-if="!collapsed" class="flex items-center gap-3">
        <div class="flex items-center justify-center w-9 h-9 bg-pink-600 rounded-lg">
          <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.17 8.17 0 004.78 1.52V6.77a4.85 4.85 0 01-1.01-.08z"/>
          </svg>
        </div>
        <span class="text-white font-bold text-lg tracking-tight">TikTok Mgr</span>
      </div>
      <button
        @click="collapsed = !collapsed"
        class="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-gray-800 transition-colors"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            :d="collapsed ? 'M13 5l7 7-7 7M5 5l7 7-7 7' : 'M11 19l-7-7 7-7m8 14l-7-7 7-7'" />
        </svg>
      </button>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 px-3 py-4 space-y-1">
      <router-link
        v-for="item in navItems"
        :key="item.name"
        :to="item.path"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group"
        :class="[
          $route.path === item.path
            ? 'bg-pink-600 text-white shadow-md'
            : 'text-gray-400 hover:bg-gray-800 hover:text-white'
        ]"
      >
        <component :is="item.icon" class="w-5 h-5 flex-shrink-0" />
        <span v-if="!collapsed" class="text-sm font-medium">{{ item.name }}</span>
      </router-link>
    </nav>

    <!-- User section -->
    <div class="px-3 py-4 border-t border-gray-800">
      <div v-if="user" class="flex items-center gap-3 px-3 py-2">
        <img
          v-if="user.picture"
          :src="user.picture"
          :alt="user.name"
          class="w-8 h-8 rounded-full flex-shrink-0 object-cover"
        />
        <div v-else class="w-8 h-8 rounded-full bg-pink-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
          {{ userInitial }}
        </div>
        <div v-if="!collapsed" class="flex-1 min-w-0">
          <p class="text-sm text-white font-medium truncate">{{ user.name }}</p>
          <p class="text-xs text-gray-500 truncate">{{ user.email }}</p>
        </div>
      </div>
      <button
        @click="logout"
        class="flex items-center gap-3 w-full px-3 py-2 text-gray-400 hover:text-red-400 hover:bg-gray-800 rounded-lg transition-colors mt-1"
      >
        <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
        <span v-if="!collapsed" class="text-sm font-medium">ログアウト</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent, h } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const collapsed = ref(false)
const user = ref(null)

const userInitial = computed(() => {
  if (!user.value?.name) return '?'
  return user.value.name.charAt(0).toUpperCase()
})

// Icon components
const DashboardIcon = defineComponent({
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M4 5a1 1 0 011-1h4a1 1 0 011 1v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm10 0a1 1 0 011-1h4a1 1 0 011 1v2a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zm10-3a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1v-7z' })
  ])
})

const UploadIcon = defineComponent({
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12' })
  ])
})

const SettingsIcon = defineComponent({
  render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }),
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2',
      d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' })
  ])
})

const navItems = [
  { name: 'ダッシュボード', path: '/dashboard', icon: DashboardIcon },
  { name: 'アップロード', path: '/upload', icon: UploadIcon },
  { name: '設定', path: '/settings', icon: SettingsIcon }
]

async function fetchUser() {
  try {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    const res = await fetch(`${baseUrl}/auth/me`, { credentials: 'include' })
    if (res.ok) {
      user.value = await res.json()
    }
  } catch {
    // ignore
  }
}

async function logout() {
  try {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    await fetch(`${baseUrl}/auth/logout`, { method: 'POST', credentials: 'include' })
  } finally {
    router.push('/login')
  }
}

onMounted(fetchUser)
</script>
