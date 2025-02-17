<template>
  <div>
    <h1>可视化编辑器</h1>
    <el-button type="primary" @click="createNewWorkflow">新建工作流</el-button>
    <div id="editor"></div>
    <el-table :data="nodeStatuses" style="width: 100%">
      <el-table-column prop="nodeName" label="节点名称" />
      <el-table-column prop="status" label="状态" />
    </el-table>
  </div>
</template>

<script>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

export default {
  setup() {
    const router = useRouter();
    const editor = ref(null);
    const nodeStatuses = ref([]);

    const createNewWorkflow = async () => {
      const response = await axios.post('/workflow/template', {
        name: '新工作流',
        description: '这是一个新工作流',
        yaml_content: ''
      });
      if (response.data) {
        router.push({ path: `/workflow/${response.data.data.id}` });
      }
    };

    const initEditor = () => {
      editor.value = {};
      fetchNodeStatuses();
    };

    const fetchNodeStatuses = async () => {
      try {
        const response = await axios.get('/workflow/status');
        nodeStatuses.value = response.data;
      } catch (error) {
        console.error('获取节点状态失败', error);
      }
    };

    return { createNewWorkflow, initEditor, editor, nodeStatuses };
  },
  mounted() {
    this.initEditor();
  }
};
</script>

<style scoped>
/* 样式定义 */
#editor {
  height: 500px;
  border: 1px solid #ccc;
}
</style> 