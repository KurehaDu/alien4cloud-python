// 路由配置
const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../components/Home.vue')
  }
]

export default routes