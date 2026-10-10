import { expect, test } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const username = process.env.E2E_USERNAME || 'codex_m8_admin_20261010'
const password = process.env.E2E_PASSWORD || 'M8Test2026'
const runId = `${Date.now()}`.slice(-9)

async function login(page) {
  await page.goto('/login')
  await page.locator('input[autocomplete="username"]').fill(username)
  await page.locator('input[autocomplete="current-password"]').fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: '工作台' })).toBeVisible()
}

async function selectOption(page, dialog, label, option) {
  const item = dialog.locator('.el-form-item').filter({ hasText: label }).first()
  await item.locator('.el-select').click()
  await page.locator('.el-select-dropdown:visible').getByText(option, { exact: true }).click()
}

test.describe('M8 管理端真实数据链路', () => {
  test('登录、组织与员工数据可保存并在刷新后读取', async ({ page, request }) => {
    const failedResponses = []
    page.on('response', (response) => {
      if (response.url().includes('/api/') && response.status() >= 500) {
        failedResponses.push(`${response.status()} ${response.url()}`)
      }
    })

    await login(page)
    const token = await page.evaluate(() => localStorage.getItem('hr_access_token'))
    expect(token).toBeTruthy()
    const headers = { Authorization: `Bearer ${token}` }

    const departmentName = `E2E部门${runId}`
    await page.getByRole('menuitem', { name: '部门管理' }).click()
    await page.getByRole('button', { name: /新增部门/ }).click()
    let dialog = page.getByRole('dialog')
    await dialog.locator('input').first().fill(departmentName)
    const departmentResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/api/departments') && response.request().method() === 'POST',
    )
    await dialog.getByRole('button', { name: '保存', exact: true }).click()
    const departmentResponse = await departmentResponsePromise
    expect(departmentResponse.ok()).toBeTruthy()
    const departmentBody = await departmentResponse.json()
    const departmentId = departmentBody.data.id
    await expect(page.locator('.el-table').getByText(departmentName, { exact: true })).toBeVisible()
    await page.reload()
    await expect(page.locator('.el-table').getByText(departmentName, { exact: true })).toBeVisible()

    const positionName = `E2E岗位${runId}`
    const positionCode = `E2E_${runId}`
    await page.getByRole('menuitem', { name: '岗位管理' }).click()
    await page.getByRole('button', { name: /新增岗位/ }).click()
    dialog = page.getByRole('dialog')
    const positionInputs = dialog.locator('input')
    await positionInputs.nth(0).fill(positionName)
    await positionInputs.nth(1).fill(positionCode)
    const positionResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/api/positions') && response.request().method() === 'POST',
    )
    await dialog.getByRole('button', { name: '保存', exact: true }).click()
    const positionResponse = await positionResponsePromise
    expect(positionResponse.ok()).toBeTruthy()
    const positionBody = await positionResponse.json()
    const positionId = positionBody.data.id
    await expect(page.locator('.el-table').getByText(positionName, { exact: true })).toBeVisible()
    await page.reload()
    await expect(page.locator('.el-table').getByText(positionCode, { exact: true })).toBeVisible()

    const employeeName = `自动化员工${runId}`
    const phone = `139${runId.slice(-8)}`
    await page.getByRole('menuitem', { name: '员工档案' }).click()
    await page.getByRole('button', { name: /新建员工/ }).click()
    dialog = page.getByRole('dialog')
    await dialog.locator('.el-form-item').filter({ hasText: '姓名' }).locator('input').fill(employeeName)
    await dialog.locator('.el-form-item').filter({ hasText: '手机号' }).locator('input').fill(phone)
    const hireDateInput = dialog
      .locator('.el-form-item')
      .filter({ hasText: '入职日期' })
      .locator('input')
    await hireDateInput.fill('2026-10-10')
    await hireDateInput.press('Enter')
    await expect(hireDateInput).toHaveValue('2026-10-10')
    await selectOption(page, dialog, '部门', departmentName)
    await selectOption(page, dialog, '岗位', positionName)
    const employeeResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/api/employees') && response.request().method() === 'POST',
    )
    await dialog.getByRole('button', { name: '保存', exact: true }).click()
    const employeeResponse = await employeeResponsePromise
    expect(employeeResponse.ok()).toBeTruthy()
    const employeeBody = await employeeResponse.json()
    const employeeId = employeeBody.data.id
    await expect(page.locator('.el-table').getByText(employeeName, { exact: true })).toBeVisible()
    await page.reload()
    const keyword = page.getByPlaceholder('姓名 / 工号 / 手机号')
    await keyword.fill(employeeName)
    await keyword.press('Enter')
    await expect(page.locator('.el-table').getByText(employeeName, { exact: true })).toBeVisible()

    const employeeDetail = await request.get(`/api/employees/${employeeId}`, { headers })
    expect(employeeDetail.ok()).toBeTruthy()
    const detailBody = await employeeDetail.json()
    expect(detailBody.data).toMatchObject({
      id: employeeId,
      name: employeeName,
      phone,
      department_id: departmentId,
      position_id: positionId,
    })

    const pages = [
      ['考勤管理', /\/attendance$/, '考勤管理'],
      ['请假审批', /\/leaves$/, '请假审批'],
      ['薪酬管理', /\/payroll$/, '薪酬管理'],
      ['消息中心', /\/messages$/, '消息中心'],
    ]
    for (const [menu, url, title] of pages) {
      await page.getByRole('menuitem', { name: menu }).click()
      await expect(page).toHaveURL(url)
      await expect(page.getByRole('heading', { name: title })).toBeVisible()
    }

    mkdirSync('e2e-artifacts', { recursive: true })
    await page.screenshot({ path: 'e2e-artifacts/m8-desktop.png', fullPage: true })
    expect(failedResponses).toEqual([])
  })

  test('移动端登录页与工作台可正常使用', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await login(page)
    await expect(page.getByText('工作台', { exact: true }).first()).toBeVisible()
    mkdirSync('e2e-artifacts', { recursive: true })
    await page.screenshot({ path: 'e2e-artifacts/m8-mobile.png', fullPage: true })
  })
})
