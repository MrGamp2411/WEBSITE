import express from 'express';
import { v4 as uuid } from 'uuid';
import { transactionService, paymentPageService, spaceId } from './walleeClient';

const app = express();
app.use(express.json());

app.post('/api/topup/init', async (req, res) => {
  try {
    const amount = Number(req.body.amount);
    if (!Number.isFinite(amount) || amount < 1 || amount > 1000) {
      return res.status(400).json({ error: 'Invalid amount' });
    }
    const fixed = Math.round(amount * 100) / 100;
    const lineItem = new (require('wallee').Wallee.model.LineItemCreate)();
    lineItem.name = `Wallet Top-up CHF ${fixed.toFixed(2)}`;
    lineItem.uniqueId = `topup-${uuid()}`;
    lineItem.sku = 'wallet-topup';
    lineItem.quantity = 1;
    lineItem.amountIncludingTax = fixed;
    lineItem.type = require('wallee').Wallee.model.LineItemType.PRODUCT;

    const txCreate = new (require('wallee').Wallee.model.TransactionCreate)();
    txCreate.lineItems = [lineItem];
    txCreate.currency = 'CHF';
    txCreate.autoConfirmationEnabled = true;
    txCreate.successUrl = `${process.env.BASE_URL}/wallet/topup/success?tid={id}`;
    txCreate.failedUrl = `${process.env.BASE_URL}/wallet/topup/failed?tid={id}`;

    const tx = await transactionService.create(spaceId, txCreate);
    const url = await paymentPageService.paymentPageUrl(spaceId, tx.body.id);
    res.json({ paymentPageUrl: url.body });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Cannot start top-up' });
  }
});

app.listen(process.env.PORT || 3000, () => {
  console.log('Topup service running');
});
