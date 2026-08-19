const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const BACKEND_URL = (process.env.BACKEND_URL || 'https://recht-technisch-backend-339540402730.europe-west1.run.app').replace(/\/$/, '');

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));

app.get('/', (req, res) => {
  res.render('index');
});

app.get('/api/test_connection', async (req, res) => {
  try {
    const response = await fetch(`${BACKEND_URL}/test_connection`);
    if (!response.ok) {
      throw new Error(`Backend response was not ok (${response.status})`);
    }

    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Failed to reach the backend API:', error);
    res.status(502).json({
      error: 'Unable to reach the backend API.',
      details: error.message,
    });
  }
});

app.listen(PORT, () => {
  console.log(`Frontend app listening on http://localhost:${PORT}`);
});
