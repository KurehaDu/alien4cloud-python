import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { createStore } from 'vuex'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import routes from './router'

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 创建状态管理实例
const store = createStore({})

// 创建Vue应用实例
const app = createApp(App)

// 使用插件
app.use(router)
app.use(store)
app.use(ElementPlus)

// 挂载应用
app.mount('#app')