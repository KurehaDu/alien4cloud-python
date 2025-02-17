<template>
  <div>
    <h1>工作流详情</h1>
    <el-card>
      <h2>{{ workflow.name }}</h2>
      <p><strong>状态:</strong> {{ workflow.status }}</p>
      <p><strong>描述:</strong> {{ workflow.description }}</p>
      <el-button type="primary" @click="goBack">返回</el-button>
    </el-card>
  </div>
</template>

<script>
export default {
  data() {
    return {
      workflow: {}
    };
  },
  methods: {
    goBack() {
      this.$router.go(-1);
    }
  },
  async mounted() {
    const id = this.$route.params.id;
    try {
      const response = await this.$http.get(`/workflow/template/${id}`);
      this.workflow = response.data;
    } catch (error) {
      this.$message.error('获取工作流详情失败');
    }
  }
};
</script>

<style scoped>
/* 样式定义 */
</style> 