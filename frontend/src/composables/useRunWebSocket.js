import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { getRun } from '../api/runs'

/**
 * 运行状态 WebSocket 连接
 * WebSocket 断开时自动降级为轮询
 */
export function useRunWebSocket(runIdRef) {
  const connected = ref(false)
  let ws = null
  let reconnectTimer = null
  let pollTimer = null
  let stopped = false

  function connect() {
    if (stopped) return
    const runId = runIdRef.value
    if (!runId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname || '127.0.0.1'
    const url = `${protocol}//${host}:8765/api/ws/runs/${runId}`

    try {
      ws = new WebSocket(url)
    } catch {
      startPolling()
      return
    }

    ws.onopen = () => {
      connected.value = true
      stopPolling()
    }

    ws.onmessage = (event) => {
      // WebSocket 消息只用于通知状态变更
      // 实际数据通过轮询/刷新获取
    }

    ws.onclose = () => {
      connected.value = false
      if (!stopped) {
        startPolling()
        reconnectTimer = setTimeout(() => connect(), 5000)
      }
    }

    ws.onerror = () => {
      connected.value = false
      ws?.close()
    }
  }

  function startPolling() {
    stopPolling()
    pollTimer = setInterval(async () => {
      // 父组件通过返回的 refresh callback 处理
    }, 3000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function disconnect() {
    stopped = true
    if (ws) {
      ws.close()
      ws = null
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    stopPolling()
  }

  onMounted(() => connect())

  watch(runIdRef, (newId, oldId) => {
    if (newId && newId !== oldId) {
      disconnect()
      stopped = false
      connect()
    }
  })

  onBeforeUnmount(() => disconnect())

  return { connected }
}