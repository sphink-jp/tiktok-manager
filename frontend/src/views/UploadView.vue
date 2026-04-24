<template>
  <Layout>
    <div class="max-w-2xl mx-auto">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="px-6 py-5 border-b border-gray-100">
          <h3 class="font-semibold text-gray-800 text-lg">TikTok 動画アップロード</h3>
          <p class="text-sm text-gray-500 mt-1">動画ファイルと投稿情報を入力してください</p>
        </div>

        <form @submit.prevent="handleUpload" class="px-6 py-6 space-y-6">
          <!-- Video file drop zone -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">動画ファイル <span class="text-red-500">*</span></label>
            <div
              class="border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer"
              :class="isDragging ? 'border-pink-400 bg-pink-50' : 'border-gray-200 hover:border-pink-300 hover:bg-pink-50/30'"
              @dragover.prevent="isDragging = true"
              @dragleave="isDragging = false"
              @drop.prevent="handleDrop"
              @click="fileInput.click()"
            >
              <input
                ref="fileInput"
                type="file"
                accept="video/*"
                class="hidden"
                @change="handleFileChange"
              />
              <div v-if="!selectedFile">
                <svg class="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p class="text-gray-500 text-sm">クリックまたはドラッグ&ドロップで動画を選択</p>
                <p class="text-gray-400 text-xs mt-1">MP4, MOV, AVI — 最大 500MB</p>
              </div>
              <div v-else class="flex items-center justify-center gap-3">
                <svg class="w-8 h-8 text-pink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <div class="text-left">
                  <p class="text-sm font-medium text-gray-800">{{ selectedFile.name }}</p>
                  <p class="text-xs text-gray-500">{{ formatFileSize(selectedFile.size) }}</p>
                </div>
                <button type="button" @click.stop="clearFile" class="text-gray-400 hover:text-red-500 ml-2">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- Title -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              タイトル <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.title"
              type="text"
              placeholder="動画のタイトルを入力（最大150文字）"
              maxlength="150"
              required
              class="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-pink-400 focus:border-transparent transition"
            />
            <p class="text-xs text-gray-400 mt-1 text-right">{{ form.title.length }} / 150</p>
          </div>

          <!-- Description -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">説明文</label>
            <textarea
              v-model="form.description"
              placeholder="動画の説明、ハッシュタグなどを入力"
              rows="4"
              maxlength="2200"
              class="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-pink-400 focus:border-transparent transition resize-none"
            ></textarea>
            <p class="text-xs text-gray-400 mt-1 text-right">{{ form.description.length }} / 2200</p>
          </div>

          <!-- Privacy -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">公開設定</label>
            <select
              v-model="form.privacy"
              class="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-pink-400 focus:border-transparent transition bg-white"
            >
              <option value="public">公開</option>
              <option value="friends">友達のみ</option>
              <option value="private">非公開</option>
            </select>
          </div>

          <!-- Status message: reconnect required -->
          <div v-if="needsTiktokReconnect" class="rounded-lg px-4 py-3 text-sm bg-red-50 text-red-700 border border-red-200">
            <p class="font-medium">
              TikTokアカウントとの連携が必要です。<router-link to="/settings" class="underline hover:text-red-900">設定ページ</router-link>でTikTokと連携してください。
            </p>
          </div>

          <!-- Status message: normal -->
          <div v-else-if="statusMessage" class="rounded-lg px-4 py-3 text-sm" :class="statusClass">
            <p class="font-medium">{{ statusMessage }}</p>
            <p v-if="publishId" class="mt-1 text-xs opacity-75">
              Publish ID: {{ publishId }}
            </p>
          </div>

          <!-- Uploading indicator -->
          <div v-if="uploading" class="flex items-center gap-3 text-sm text-gray-500">
            <svg class="w-5 h-5 animate-spin text-pink-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>{{ uploadStepMessage }}</span>
          </div>

          <!-- Submit -->
          <div class="flex gap-3 pt-2">
            <button
              type="submit"
              :disabled="uploading || !selectedFile || !form.title"
              class="flex-1 bg-pink-600 hover:bg-pink-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              <svg v-if="!uploading" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <svg v-else class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {{ uploading ? 'TikTokへ投稿中...' : 'TikTokへ投稿' }}
            </button>
            <button
              type="button"
              @click="resetForm"
              class="px-6 py-3 border border-gray-200 text-gray-600 hover:bg-gray-50 rounded-xl transition-colors font-medium"
            >
              リセット
            </button>
          </div>
        </form>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import Layout from '../components/Layout.vue'
import { useApiWithRefresh } from '../composables/useApiWithRefresh.js'

const fileInput = ref(null)
const selectedFile = ref(null)
const isDragging = ref(false)
const uploading = ref(false)
const uploadStepMessage = ref('')
const statusMessage = ref('')
const statusType = ref('') // 'success' | 'error'
const publishId = ref('')

const { callWithRefresh, needsTiktokReconnect, baseUrl } = useApiWithRefresh()

const form = reactive({
  title: '',
  description: '',
  privacy: 'public',
})

const statusClass = computed(() => {
  return statusType.value === 'success'
    ? 'bg-green-50 text-green-700 border border-green-200'
    : 'bg-red-50 text-red-700 border border-red-200'
})

function handleFileChange(event) {
  const file = event.target.files[0]
  if (file) selectedFile.value = file
}

function handleDrop(event) {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file && file.type.startsWith('video/')) {
    selectedFile.value = file
  }
}

function clearFile() {
  selectedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function resetForm() {
  clearFile()
  form.title = ''
  form.description = ''
  form.privacy = 'public'
  statusMessage.value = ''
  statusType.value = ''
  uploadStepMessage.value = ''
  publishId.value = ''
  needsTiktokReconnect.value = false
}

async function handleUpload() {
  if (!selectedFile.value || !form.title) return

  uploading.value = true
  statusMessage.value = ''
  publishId.value = ''
  needsTiktokReconnect.value = false
  uploadStepMessage.value = 'TikTokへ動画を送信しています...'

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('title', form.title)
  formData.append('description', form.description)
  formData.append('privacy', form.privacy)

  try {
    const res = await callWithRefresh(() =>
      fetch(`${baseUrl}/api/upload`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      })
    )

    if (needsTiktokReconnect.value) return

    if (res.ok) {
      const data = await res.json()
      publishId.value = data.publish_id ?? ''
      statusType.value = 'success'
      statusMessage.value = 'TikTokへの投稿が完了しました。数分後にTikTokアプリで確認できます。'
      clearFile()
      form.title = ''
      form.description = ''
      form.privacy = 'public'
    } else {
      const err = await res.json().catch(() => ({ detail: 'アップロードに失敗しました' }))
      statusType.value = 'error'
      statusMessage.value = err.detail ?? 'アップロードに失敗しました'
    }
  } catch {
    statusType.value = 'error'
    statusMessage.value = 'ネットワークエラーが発生しました'
  } finally {
    uploading.value = false
    uploadStepMessage.value = ''
  }
}
</script>
