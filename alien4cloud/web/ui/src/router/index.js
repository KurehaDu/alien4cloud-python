// 路由配置
const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../components/Home.vue')
  },
  {
    path: '/workflow',
    name: 'WorkflowManager',
    component: () => import('../components/workflow/WorkflowManager.vue')
  },
  {
    path: '/workflow/:id',
    name: 'WorkflowDetail',
    component: () => import('../components/workflow/WorkflowDetail.vue')
  },
  {
    path: '/editor',
    name: 'WorkflowEditor',
    component: () => import('../components/workflow/WorkflowEditor.vue')
  },
  {
    path: '/editor/:id',
    name: 'WorkflowEditorWithId',
    component: () => import('../components/workflow/WorkflowEditor.vue')
  }
]

export default routes