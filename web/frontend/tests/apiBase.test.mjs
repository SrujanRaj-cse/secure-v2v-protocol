import test from 'node:test'
import assert from 'node:assert/strict'
import { resolveApiBase } from '../src/services/apiBase.mjs'

test('development always uses the same-origin Vite API proxy', () => {
  assert.equal(resolveApiBase(true, 'https://secure-v2v-protocol.onrender.com'), '/api')
})

test('production accepts an origin and appends the API prefix', () => {
  assert.equal(resolveApiBase(false, 'https://api.example.test/'), 'https://api.example.test/api')
})

test('production does not duplicate an API prefix in an existing value', () => {
  assert.equal(resolveApiBase(false, 'https://api.example.test/api/'), 'https://api.example.test/api')
})

test('empty configuration uses relative API paths', () => {
  assert.equal(resolveApiBase(false, ''), '/api')
})
