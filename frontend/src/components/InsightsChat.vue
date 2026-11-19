<!-- Copyright (c) 2026 Lumen Solutions. All rights reserved.
     SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
     Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions. -->
<template>
  <section class="panel insights" :aria-label="t('Insights chat')">
    <header class="chat-header">
      <div>
        <h2>{{ t('Insights chat') }}</h2>
        <p>{{ t('Gemini analyzes aggregate results you have permission to see.') }}</p>
      </div>
      <button class="lbtn sm" type="button" :disabled="pending || !messages.length" @click="reset">
        {{ t('New chat') }}
      </button>
    </header>

    <div ref="thread" class="thread" role="log" :aria-label="t('Conversation')">
      <div v-if="!messages.length" class="chat-welcome">
        <h3>{{ t('What would you like to understand?') }}</h3>
        <p>{{ t('Ask about a metric, compare periods, or follow up on what changed.') }}</p>
        <div class="examples">
          <button v-for="example in examples" :key="example" class="chip" type="button" @click="send(t(example))">
            {{ t(example) }}
          </button>
        </div>
      </div>

      <article v-for="(message, index) in messages" :key="index" class="message" :class="message.role">
        <div class="speaker">{{ message.role === 'user' ? t('You') : t('Insights assistant') }}</div>
        <p class="message-text" dir="auto">{{ message.role === 'user' ? message.text : t(message.text) }}</p>
        <details v-if="message.evidence?.length" class="evidence">
          <summary>{{ t('Data used ({0})', message.evidence.length) }}</summary>
          <div v-for="(item, source) in message.evidence" :key="source" class="source">
            <strong dir="auto">{{ item.query.doctype }}</strong>
            <div dir="ltr" class="measure">
              {{ item.query.aggregate.function }}({{ item.query.aggregate.field || '*' }})
              <template v-if="item.query.group_by">
                · {{ item.query.group_by.field }}
                <template v-if="item.query.group_by.time_grain"> / {{ item.query.group_by.time_grain }}</template>
              </template>
            </div>
            <ul v-if="item.query.filters.length" class="scope">
              <li v-for="([field, operator, value], i) in item.query.filters" :key="i" dir="auto">
                {{ field }} {{ operator }} {{ Array.isArray(value) ? value.join(', ') : value }}
              </li>
            </ul>
            <strong v-if="!item.rows" dir="ltr">{{ item.value }}</strong>
            <dl v-else class="result-grid">
              <template v-for="(row, i) in item.rows" :key="i">
                <dt dir="auto">{{ row.label }}</dt><dd dir="ltr">{{ row.value }}</dd>
              </template>
            </dl>
            <small v-if="item.partial">{{ t('Showing the first {0} groups.', item.rows.length) }}</small>
          </div>
        </details>
      </article>
      <p v-if="pending" class="thinking">{{ t('Thinking…') }}</p>
    </div>

    <form class="composer" @submit.prevent="send()">
      <p v-if="error" class="chat-error" role="alert" dir="auto">{{ error }}</p>
      <div class="compose-row">
        <div class="lfield">
          <label for="insights-question" class="sr-only">{{ t('Business question') }}</label>
          <textarea
            id="insights-question"
            ref="input"
            v-model="draft"
            dir="auto"
            rows="2"
            maxlength="2000"
            :disabled="pending"
            :placeholder="t('Ask a business question…')"
            @keydown.enter.exact="submitOnEnter"
          ></textarea>
        </div>
        <button class="lbtn primary" type="submit" :disabled="pending || !draft.trim()">{{ t('Send') }}</button>
      </div>
    </form>
  </section>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { call } from 'frappe-ui'
import { serverMessage } from '@/lib/brand'
import { t } from '@/lib/i18n'

const examples = [
  'Compare POS sales this month and last month',
  'Show sales by month this year',
  'What is the total on overdue sales invoices?',
]
const messages = ref([])
const draft = ref('')
const pending = ref(false)
const error = ref('')
const thread = ref(null)
const input = ref(null)

async function scrollToLatest() {
  await nextTick()
  if (thread.value) thread.value.scrollTop = thread.value.scrollHeight
}

async function send(text = draft.value) {
  const prompt = text.trim()
  if (!prompt || pending.value) return
  const history = messages.value.slice(-10).map(({ role, text }) => ({ role, text }))
  messages.value.push({ role: 'user', text: prompt })
  draft.value = ''
  error.value = ''
  pending.value = true
  scrollToLatest()
  try {
    const result = await call('lumen_reports.insights.discuss', { prompt, history })
    messages.value.push({ role: 'assistant', text: result.text, evidence: result.evidence })
  } catch (failure) {
    messages.value.pop()
    draft.value = prompt
    error.value = t(serverMessage(failure) || 'Could not send your question. Try again.')
  } finally {
    pending.value = false
    await scrollToLatest()
    input.value?.focus({ preventScroll: true })
  }
}

function submitOnEnter(event) {
  if (event.isComposing) return
  event.preventDefault()
  send()
}

async function reset() {
  messages.value = []
  draft.value = ''
  error.value = ''
  await nextTick()
  input.value?.focus()
}
</script>

<style scoped>
.insights { overflow: hidden; }
.chat-header, .composer { padding: 16px 20px; }
.chat-header { display: flex; align-items: start; justify-content: space-between; gap: 14px; border-bottom: 1px solid var(--border); }
.chat-header h2 { font-size: 16px; font-weight: 750; }
.chat-header button { flex: none; }
.chat-header p, .chat-welcome p, .thinking { color: var(--muted); font-size: 13px; }
.thread { min-height: 260px; max-height: 55vh; overflow-y: auto; padding: 22px 20px; }
.chat-welcome { max-width: 510px; margin: 32px auto; text-align: center; }
.chat-welcome h3 { font-size: 21px; font-weight: 750; margin-bottom: 5px; }
.examples { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 18px; }
.message { width: fit-content; max-width: min(88%, 650px); padding: 11px 14px; border-radius: 13px; margin: 0 0 14px; }
.message.user { margin-inline-start: auto; background: var(--blue); color: var(--on-brand, white); }
.message.assistant { border: 1px solid var(--border); background: var(--bg); }
.speaker { font-size: 11px; font-weight: 750; margin-bottom: 3px; }
.message-text { font-size: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }
.evidence { border-top: 1px solid var(--border); margin-top: 10px; padding-top: 7px; font-size: 12px; }
.evidence summary { cursor: pointer; font-weight: 650; color: var(--blue); }
.source { margin-top: 8px; padding: 8px; border-radius: 7px; background: var(--panel); overflow-wrap: anywhere; }
.measure, .scope, .source small { color: var(--muted); }
.measure { text-align: start; }
.scope { margin: 4px 0; padding-inline-start: 15px; list-style: disc; }
.result-grid { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 12px; margin-top: 4px; }
.result-grid dd { font-variant-numeric: tabular-nums; }
.composer { border-top: 1px solid var(--border); }
.compose-row { display: flex; gap: 10px; align-items: end; }
.compose-row .lfield { flex: 1; min-width: 0; }
.compose-row textarea {
  min-height: 64px;
  width: 100%;
  padding: 9px 11px;
  border: 1px solid var(--border-2);
  border-radius: 9px;
  background: var(--bg);
  color: var(--ink);
  font-size: 14px;
  resize: vertical;
}
.compose-row button { flex: none; }
.chat-error { color: var(--danger); font-size: 13px; margin-bottom: 8px; }
@media (max-width: 560px) {
  .chat-header, .composer, .thread { padding-inline: 12px; }
  .thread { min-height: 230px; max-height: 40vh; }
  .message { max-width: 95%; }
  .chat-welcome { margin-block: 10px; }
}
</style>
