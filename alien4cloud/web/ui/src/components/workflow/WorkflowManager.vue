<template>
  <div>
    <h1>工作流管理</h1>
    <el-button type="primary" @click="uploadYaml">上传YAML文件</el-button>
    <el-table :data="workflows" style="width: 100%">
      <el-table-column prop="name" label="工作流名称" />
      <el-table-column prop="status" label="状态" />
      <el-table-column label="操作">
        <template v-slot="scope">
          <el-button @click="viewWorkflow(scope.row.id)">查看</el-button>
          <el-button @click="deployWorkflow(scope.row.id)">部署</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script>
export default {
  data() {
    return {
      workflows: []
    };
  },
  methods: {
    async uploadYaml() {
      const fileInput = document.createElement('input');
      fileInput.type = 'file';
      fileInput.accept = '.yaml, .yml';
      fileInput.onchange = async (event) => {
        const file = event.target.files[0];
        if (file) {
          const formData = new FormData();
          formData.append('file', file);
          try {
            const response = await this.$http.post('/workflow/upload', formData);
            this.$message.success('上传成功');
            // TODO: 更新工作流列表
            this.fetchWorkflows();
          } catch (error) {
            this.$message.error('上传失败');
          }
        }
      };
      fileInput.click();
    },
    async fetchWorkflows() {
      try {
        const response = await this.$http.get('/workflow/template');
        this.workflows = response.data;
      } catch (error) {
        this.$message.error('获取工作流列表失败');
      }
    },
    async viewWorkflow(id) {
      try {
        const response = await this.$http.get(`/workflow/template/${id}`);
        // TODO: 显示工作流详细信息的逻辑
        this.$message.success('工作流详情获取成功');
      } catch (error) {
        this.$message.error('获取工作流详情失败');
      }
    },
    async deployWorkflow(id) {
      try {
        const response = await this.$http.post(`/workflow/deploy/${id}`);
        this.$message.success('工作流部署成功');
      } catch (error) {
        this.$message.error('工作流部署失败');
      }
    }
  },
  mounted() {
    this.fetchWorkflows();
  }
};
</script>

<style scoped>
/* 样式定义 */
</style> 