// Owner: Dev D
import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { ROLES, ROLE_HOME, canAccess, routeAfterRoleChange, routeFor } from '../src/lib/roles.ts'

describe('role routing', () => {
  it('sends each role to its home route', () => {
    assert.deepEqual(ROLE_HOME, {
      institution_admin: '/institution',
      institution_operator: '/institution',
      aicte_admin: '/aicte',
      auditor: '/aicte',
      student: '/student',
      verifier: '/verifier',
    })
    for (const role of ROLES) assert.ok(canAccess(role, ROLE_HOME[role]), role)
  })

  it('stays on an allowed route and leaves a forbidden one', () => {
    assert.equal(routeAfterRoleChange('student', '/institution'), '/student')
    assert.equal(routeAfterRoleChange('verifier', '/student'), '/verifier')
    assert.equal(routeAfterRoleChange('aicte_admin', '/blindmatch'), '/blindmatch')
    assert.equal(routeAfterRoleChange('aicte_admin', '/verifier'), '/verifier')
    assert.equal(routeAfterRoleChange('auditor', '/aicte/reports'), '/aicte/reports')
    assert.equal(routeAfterRoleChange('student', '/blindmatch'), '/student')
  })

  it('lets every role use home and unknown paths', () => {
    for (const role of ROLES) {
      assert.ok(canAccess(role, '/'), role)
      assert.ok(canAccess(role, '/no-such-page'), role)
    }
  })

  it('matches nested paths but not prefixes of other words', () => {
    assert.equal(routeFor('/aicte/reports')?.path, '/aicte')
    assert.equal(routeFor('/aicteish'), undefined)
    assert.deepEqual(routeFor('/institution')?.roles, ['institution_admin', 'institution_operator'])
  })
})
