import WorkflowDetail from '../components/workflow/WorkflowDetail.vue';
import WorkflowEditor from '../components/workflow/WorkflowEditor.vue';

const routes = [
  // ...其他路由
  {
    path: '/workflow/detail/:id',
    name: 'WorkflowDetail',
    component: WorkflowDetail
  },
  {
    path: '/workflow/editor',
    name: 'WorkflowEditor',
    component: WorkflowEditor
  }
]; 