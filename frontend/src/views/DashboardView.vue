<template>
  <Layout>
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
          <p class="text-2xl font-bold text-gray-800 mt-0.5">{{ stat.value }}</p>
          <p class="text-xs mt-0.5" :class="stat.changePositive ? 'text-green-500' : 'text-red-400'">
            {{ stat.change }}
          </p>
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
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50">
            <tr>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">タイトル</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">投稿日時</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">ビュー数</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">いいね</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">ステータス</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="video in recentVideos" :key="video.id" class="hover:bg-gray-50 transition-colors">
              <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-pink-400 to-purple-500 flex-shrink-0"></div>
                  <span class="font-medium text-gray-800 truncate max-w-[200px]">{{ video.title }}</span>
                </div>
              </td>
              <td class="px-6 py-4 text-gray-500">{{ video.date }}</td>
              <td class="px-6 py-4 text-gray-700 font-medium">{{ video.views }}</td>
              <td class="px-6 py-4 text-gray-700 font-medium">{{ video.likes }}</td>
              <td class="px-6 py-4">
                <span
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                  :class="statusClass(video.status)"
                >
                  {{ video.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { defineComponent, h } from 'vue'
import Layout from '../components/Layout.vue'

// Icon components
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

const stats = [
  { label: '総アップロード数', value: '142', change: '↑ 先月比 +12%', changePositive: true, icon: VideoIcon, bgColor: 'bg-pink-50', iconColor: 'text-pink-500' },
  { label: '今月のビュー数', value: '1.2M', change: '↑ 先月比 +8%', changePositive: true, icon: EyeIcon, bgColor: 'bg-blue-50', iconColor: 'text-blue-500' },
  { label: 'いいね合計', value: '48.3K', change: '↑ 先月比 +21%', changePositive: true, icon: HeartIcon, bgColor: 'bg-red-50', iconColor: 'text-red-500' },
  { label: 'エンゲージメント率', value: '4.2%', change: '↓ 先月比 -0.3%', changePositive: false, icon: TrendIcon, bgColor: 'bg-green-50', iconColor: 'text-green-500' }
]

const recentVideos = [
  { id: 1, title: '春の桜スポット巡り 2024', date: '2024-04-20 14:32', views: '28,412', likes: '1,203', status: '公開中' },
  { id: 2, title: '簡単パスタレシピ10選', date: '2024-04-19 09:15', views: '15,887', likes: '892', status: '公開中' },
  { id: 3, title: 'AIツール比較レビュー', date: '2024-04-17 18:00', views: '42,301', likes: '3,102', status: '公開中' },
  { id: 4, title: '東京カフェめぐり Vol.3', date: '2024-04-15 12:00', views: '9,244', likes: '567', status: '審査中' },
  { id: 5, title: '朝活ルーティン公開', date: '2024-04-14 06:30', views: '33,100', likes: '2,441', status: '公開中' }
]

function statusClass(status) {
  const map = {
    '公開中': 'bg-green-100 text-green-700',
    '審査中': 'bg-yellow-100 text-yellow-700',
    '非公開': 'bg-gray-100 text-gray-600',
    'エラー': 'bg-red-100 text-red-700'
  }
  return map[status] ?? 'bg-gray-100 text-gray-600'
}
</script>
