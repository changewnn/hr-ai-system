<template>
  <div class="employee-agent-page">
    <PageHeader title="智能助手" description="基于已发布 HR 政策回答问题，回答会附带可核验出处" />
    <section class="agent-layout panel">
      <aside class="agent-conversations">
        <div class="agent-side-heading"><strong>我的会话</strong><el-button text circle :icon="Plus" title="新建会话" @click="newConversation" /></div>
        <el-scrollbar class="conversation-scroll">
          <button v-for="item in conversations" :key="item.id" class="conversation-item" :class="{ active: item.id === activeId }" @click="selectConversation(item.id)">
            <span>{{ item.title || '新会话' }}</span><small>{{ formatDateTime(item.updated_at) }}</small>
          </button>
        </el-scrollbar>
      </aside>
      <div class="agent-chat">
        <div v-if="!activeId" class="agent-empty"><el-icon :size="34"><ChatDotRound /></el-icon><strong>开始政策问答</strong><span>例如：年假如何申请？病假需要提交什么材料？</span></div>
        <template v-else>
          <el-scrollbar ref="chatScrollbar" class="chat-scroll"><div class="chat-messages">
            <article v-for="message in messages" :key="message.id || message.localId" class="chat-message" :class="message.role.toLowerCase()">
              <div class="chat-role">{{ message.role === 'USER' ? '我' : '助手' }}</div>
              <div class="chat-bubble"><p>{{ message.content }}</p>
                <div v-if="message.citations?.length" class="citation-list"><strong>政策出处</strong><button v-for="citation in message.citations" :key="citation.chunk_id" class="citation" @click="showCitation(citation)">{{ citation.document_name }} · {{ citation.version }} · {{ citation.section || '政策片段' }}</button></div>
                <el-tag v-if="message.transferred_to_hr" type="warning" effect="plain">已转交 HR</el-tag>
              </div>
            </article>
            <div v-if="sending" class="agent-typing"><el-icon class="is-loading"><Loading /></el-icon> 正在检索政策并生成回答</div>
          </div></el-scrollbar>
          <div class="agent-composer"><el-input v-model="question" type="textarea" :rows="2" maxlength="4000" show-word-limit placeholder="请输入关于公司政策的问题" @keydown.enter.exact.prevent="send" /><div class="composer-footer"><span>仅回答已发布政策；无可靠依据时会转交 HR</span><el-button type="primary" :loading="sending" :icon="Promotion" @click="send">发送</el-button></div></div>
        </template>
      </div>
    </section>
    <el-dialog v-model="citationVisible" title="政策出处" width="620"><div v-if="selectedCitation" class="citation-detail"><div><span>文档</span><strong>{{ selectedCitation.document_name }}</strong></div><div><span>版本</span><strong>{{ selectedCitation.version }}</strong></div><div v-if="selectedCitation.section"><span>章节</span><strong>{{ selectedCitation.section }}</strong></div><div v-if="selectedCitation.page_number"><span>页码</span><strong>第 {{ selectedCitation.page_number }} 页</strong></div><p>{{ selectedCitation.excerpt }}</p></div></el-dialog>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Loading, Plus, Promotion } from '@element-plus/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import { agentApi } from '../../api'
import { formatDateTime } from '../../utils/datetime'
const conversations = ref([]), activeId = ref(null), messages = ref([]), question = ref(''), sending = ref(false), chatScrollbar = ref(null), citationVisible = ref(false), selectedCitation = ref(null)
async function loadConversations() { try { conversations.value = (await agentApi.conversations()).data || []; if (conversations.value.length && !activeId.value) await selectConversation(conversations.value[0].id) } catch (e) { ElMessage.error(e.businessMessage) } }
async function newConversation() { try { const result = await agentApi.createConversation(); conversations.value.unshift(result.data); await selectConversation(result.data.id) } catch (e) { ElMessage.error(e.businessMessage) } }
async function selectConversation(id) { try { const result = await agentApi.conversation(id); activeId.value = id; messages.value = result.data?.messages || []; await scrollBottom() } catch (e) { ElMessage.error(e.businessMessage) } }
async function send() {
  const content = question.value.trim(); if (!content || sending.value) return
  if (!activeId.value) await newConversation(); const conversationId = activeId.value
  messages.value.push({ localId: `user-${Date.now()}`, role: 'USER', content, citations: [] }); question.value = ''; sending.value = true
  const assistant = { localId: `assistant-${Date.now()}`, role: 'ASSISTANT', content: '', citations: [], transferred_to_hr: false }; messages.value.push(assistant)
  try {
    const response = await fetch(agentApi.streamUrl(conversationId), { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('hr_access_token')}` }, body: JSON.stringify({ content }) })
    if (!response.ok) throw new Error((await response.json()).message || '助手请求失败')
    const reader = response.body.getReader(), decoder = new TextDecoder(); let buffer = ''
    while (true) { const { value, done } = await reader.read(); if (done) break; buffer += decoder.decode(value, { stream: true }); const blocks = buffer.split('\n\n'); buffer = blocks.pop() || ''; for (const block of blocks) { const event = block.match(/^event: (.+)$/m)?.[1], data = block.match(/^data: (.+)$/m)?.[1]; if (!event || !data) continue; const payload = JSON.parse(data); if (event === 'message_delta') assistant.content += payload.delta || ''; if (event === 'citation') assistant.citations.push(payload); if (event === 'hr_transferred') assistant.transferred_to_hr = true } await scrollBottom() }
    await loadConversations()
  } catch (e) { messages.value = messages.value.filter((item) => item !== assistant); ElMessage.error(e.businessMessage || e.message || '助手请求失败') } finally { sending.value = false; await scrollBottom() }
}
function showCitation(citation) { selectedCitation.value = citation; citationVisible.value = true }
async function scrollBottom() { await nextTick(); const wrap = chatScrollbar.value?.wrapRef; if (wrap) wrap.scrollTop = wrap.scrollHeight }
onMounted(loadConversations)
</script>

<style scoped>
.agent-layout{display:grid;grid-template-columns:250px 1fr;min-height:620px;padding:0;overflow:hidden}.agent-conversations{border-right:1px solid #e8edf2;display:flex;flex-direction:column}.agent-side-heading{height:58px;padding:0 14px 0 18px;border-bottom:1px solid #edf0f3;display:flex;align-items:center;justify-content:space-between}.conversation-scroll{flex:1}.conversation-item{border:0;background:transparent;width:100%;padding:13px 17px;display:flex;flex-direction:column;gap:5px;text-align:left;cursor:pointer;border-left:3px solid transparent}.conversation-item:hover{background:#f5f8fb}.conversation-item.active{background:#eef5ff;border-left-color:#3979db}.conversation-item span{font-size:13px;color:#334155;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.conversation-item small{font-size:11px;color:#9aa5b1}.agent-chat{min-width:0;display:flex;flex-direction:column}.agent-empty{flex:1;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:10px;color:#82909e}.agent-empty strong{color:#475569}.agent-empty span{font-size:12px}.chat-scroll{flex:1;padding:22px 26px}.chat-messages{max-width:820px;margin:0 auto}.chat-message{display:flex;gap:10px;margin-bottom:20px}.chat-message.user{flex-direction:row-reverse}.chat-role{font-size:11px;color:#8b97a5;padding-top:8px;width:28px}.chat-bubble{max-width:min(76%,680px);background:#f3f6fa;border-radius:8px;padding:11px 14px;color:#334155}.chat-message.user .chat-bubble{background:#e8f1ff}.chat-bubble p{white-space:pre-wrap;line-height:1.65;margin:0;font-size:13px}.citation-list{display:flex;flex-direction:column;gap:6px;border-top:1px solid rgba(100,116,139,.18);margin-top:10px;padding-top:9px}.citation-list strong{font-size:11px;color:#64748b}.citation{border:0;background:transparent;color:#3979db;text-align:left;padding:0;font-size:11px;cursor:pointer}.agent-typing{font-size:12px;color:#8794a2;display:flex;align-items:center;gap:6px}.agent-composer{border-top:1px solid #e8edf2;padding:15px 22px;background:#fff}.composer-footer{display:flex;justify-content:space-between;align-items:center;margin-top:8px;color:#94a0ad;font-size:11px}.citation-detail{display:flex;flex-direction:column;gap:10px}.citation-detail>div{display:flex;gap:16px}.citation-detail span{color:#82909e;width:50px}.citation-detail p{white-space:pre-wrap;line-height:1.8;background:#f7f9fb;padding:14px;border-radius:6px;font-size:13px}@media(max-width:760px){.agent-layout{grid-template-columns:1fr;min-height:680px}.agent-conversations{display:none}.chat-scroll{padding:18px 12px}.chat-bubble{max-width:84%}}
</style>
