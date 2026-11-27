const crypto = require('crypto');
const fs = require('fs/promises');
const path = require('path');
const express = require('express');
const jwt = require('jsonwebtoken');

const app = express();
const port = Number(process.env.PORT || 3000);
const dataFile = process.env.DATA_FILE || path.join(__dirname, 'data', 'catalog.json');
const adminPin = process.env.ADMIN_PIN || '0206';
const jwtSecret = process.env.JWT_SECRET || 'change-this-in-render-environment-settings';

app.disable('x-powered-by');
app.use(express.json({ limit: '1mb' }));
app.use(express.static(path.join(__dirname, 'public'), { extensions: ['html'] }));

let writeQueue = Promise.resolve();

async function readStore() {
  try {
    const raw = await fs.readFile(dataFile, 'utf8');
    const parsed = JSON.parse(raw);
    return { items: Array.isArray(parsed.items) ? parsed.items : [] };
  } catch (error) {
    if (error.code === 'ENOENT') return { items: [] };
    throw error;
  }
}

function queueWrite(store) {
  writeQueue = writeQueue.then(async () => {
    await fs.mkdir(path.dirname(dataFile), { recursive: true });
    const temporary = `${dataFile}.${process.pid}.tmp`;
    await fs.writeFile(temporary, `${JSON.stringify(store, null, 2)}\n`, 'utf8');
    await fs.rename(temporary, dataFile);
  });
  return writeQueue;
}

function cleanText(value, maxLength = 120) {
  return String(value || '').trim().replace(/\s+/g, ' ').slice(0, maxLength);
}

function itemFromBody(body, existing = {}) {
  const name = cleanText(body.name, 100);
  const category = cleanText(body.category, 50);
  const description = cleanText(body.description, 400);
  const imageUrl = cleanText(body.imageUrl, 600);
  const price = Number(body.price);

  if (!name || !category || !Number.isFinite(price) || price < 0) {
    const error = new Error('Name, category, and a valid non-negative price are required.');
    error.status = 400;
    throw error;
  }
  if (imageUrl && !/^https?:\/\//i.test(imageUrl)) {
    const error = new Error('Image URL must begin with http:// or https://');
    error.status = 400;
    throw error;
  }

  return {
    ...existing,
    name,
    category,
    description,
    imageUrl,
    price: Math.round(price * 100) / 100,
    inStock: body.inStock !== false,
    updatedAt: new Date().toISOString()
  };
}

function requireAdmin(req, res, next) {
  const token = req.get('authorization')?.replace(/^Bearer\s+/i, '');
  if (!token) return res.status(401).json({ error: 'Admin sign-in required.' });
  try {
    req.admin = jwt.verify(token, jwtSecret);
    next();
  } catch {
    res.status(401).json({ error: 'Your admin session has expired. Please sign in again.' });
  }
}

app.get('/api/health', (_req, res) => res.json({ ok: true }));

app.get('/api/items', async (req, res, next) => {
  try {
    const { category = '', q = '' } = req.query;
    const search = cleanText(q, 100).toLowerCase();
    const requestedCategory = cleanText(category, 50).toLowerCase();
    const store = await readStore();
    const items = store.items.filter((item) => {
      const matchesCategory = !requestedCategory || item.category.toLowerCase() === requestedCategory;
      const matchesSearch = !search || [item.name, item.category, item.description].join(' ').toLowerCase().includes(search);
      return matchesCategory && matchesSearch;
    });
    res.json({ items });
  } catch (error) { next(error); }
});

app.post('/api/auth/login', (req, res) => {
  const enteredPin = String(req.body?.pin || '');
  const expected = Buffer.from(adminPin);
  const submitted = Buffer.from(enteredPin);
  const matches = expected.length === submitted.length && crypto.timingSafeEqual(expected, submitted);
  if (!matches) return res.status(401).json({ error: 'Incorrect PIN.' });
  const token = jwt.sign({ role: 'admin' }, jwtSecret, { expiresIn: '12h' });
  res.json({ token });
});

app.post('/api/auth/logout', (_req, res) => res.status(204).end());

app.get('/api/admin/items', requireAdmin, async (_req, res, next) => {
  try {
    const store = await readStore();
    res.json({ items: store.items });
  } catch (error) { next(error); }
});

app.post('/api/admin/items', requireAdmin, async (req, res, next) => {
  try {
    const store = await readStore();
    const item = itemFromBody(req.body, { id: crypto.randomUUID(), createdAt: new Date().toISOString() });
    store.items.unshift(item);
    await queueWrite(store);
    res.status(201).json({ item });
  } catch (error) { next(error); }
});

app.patch('/api/admin/items/:id', requireAdmin, async (req, res, next) => {
  try {
    const store = await readStore();
    const index = store.items.findIndex((item) => item.id === req.params.id);
    if (index < 0) return res.status(404).json({ error: 'Item not found.' });
    const item = itemFromBody(req.body, store.items[index]);
    store.items[index] = item;
    await queueWrite(store);
    res.json({ item });
  } catch (error) { next(error); }
});

app.delete('/api/admin/items/:id', requireAdmin, async (req, res, next) => {
  try {
    const store = await readStore();
    const remaining = store.items.filter((item) => item.id !== req.params.id);
    if (remaining.length === store.items.length) return res.status(404).json({ error: 'Item not found.' });
    store.items = remaining;
    await queueWrite(store);
    res.status(204).end();
  } catch (error) { next(error); }
});

app.get('/admin', (_req, res) => res.sendFile(path.join(__dirname, 'public', 'admin.html')));

app.use((error, _req, res, _next) => {
  console.error(error);
  res.status(error.status || 500).json({ error: error.status ? error.message : 'Something went wrong. Please try again.' });
});

app.listen(port, () => console.log(`Vishwakarma Hardware is running on port ${port}`));
