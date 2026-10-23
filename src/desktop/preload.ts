import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('workbench', {
  invoke: (action: string, arguments_: Record<string, unknown> = {}) => ipcRenderer.invoke('workbench', action, arguments_)
})
