const axios = require('axios');

async function executeShortStraddle(bridgeUrl, { underlying, expiry, lots, stopLoss }) {
    console.log(`Executing Short Straddle for ${underlying}, Expiry: ${expiry}, Lots: ${lots}`);
    const spotRes = await axios.get(`${bridgeUrl}/spot`, { params: { symbol: underlying } });
    if (spotRes.data.status !== 'success' || !spotRes.data.quote?.message?.[0]) {
        throw new Error(spotRes.data.message || "Failed to fetch spot price");
    }
    const spotPrice = parseFloat(spotRes.data.quote.message[0].last_traded_price);
    const strikesRes = await axios.get(`${bridgeUrl}/strikes`, { params: { symbol: underlying, expiry } });
    const strikes = strikesRes.data.strikes || [];
    const atmStrikeValue = Math.round(spotPrice / (underlying === 'NIFTY' ? 50 : 100)) * (underlying === 'NIFTY' ? 50 : 100);
    const ceStrike = strikes.find(s => parseFloat(s.pStrikePrice) === atmStrikeValue && s.pOptionType === 'CE');
    const peStrike = strikes.find(s => parseFloat(s.pStrikePrice) === atmStrikeValue && s.pOptionType === 'PE');
    if (!ceStrike || !peStrike) throw new Error("ATM Strikes not found");

    const lotSize = parseInt(ceStrike.pLotSize) || (underlying === 'NIFTY' ? 65 : 20);
    const quantity = lots * lotSize;

    const ceOrder = await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: ceStrike.pTrdSymbol, transaction_type: 'S', quantity, order_type: 'MKT' });
    const peOrder = await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: peStrike.pTrdSymbol, transaction_type: 'S', quantity, order_type: 'MKT' });

    // Fetch real-time quotes for entry prices and SL calculation
    const quotesRes = await axios.post(`${bridgeUrl}/quotes`, {
        tokens: [
            { instrument_token: ceStrike.pSymbol, exchange_segment: 'nse_fo' },
            { instrument_token: peStrike.pSymbol, exchange_segment: 'nse_fo' }
        ]
    });

    if (quotesRes.data.status !== 'success' || !quotesRes.data.data?.message) {
        throw new Error("Failed to fetch quotes for orders");
    }

    const quotes = quotesRes.data.data.message;
    const ceQuote = quotes.find(q => q.instrument_token === ceStrike.pSymbol);
    const peQuote = quotes.find(q => q.instrument_token === peStrike.pSymbol);

    if (!ceQuote || !peQuote) throw new Error("Quotes for placed orders not found");

    const ceLtp = parseFloat(ceQuote.last_traded_price);
    const peLtp = parseFloat(peQuote.last_traded_price);

    if (stopLoss > 0) {
        await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: ceStrike.pTrdSymbol, transaction_type: 'B', quantity, order_type: 'SL-LMT', trigger_price: (ceLtp * (1 + stopLoss/100)).toFixed(2), price: (ceLtp * (1 + stopLoss/100) + 1).toFixed(2) });
        await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: peStrike.pTrdSymbol, transaction_type: 'B', quantity, order_type: 'SL-LMT', trigger_price: (peLtp * (1 + stopLoss/100)).toFixed(2), price: (peLtp * (1 + stopLoss/100) + 1).toFixed(2) });
    }

    return {
        status: 'success',
        ceOrder: ceOrder.data,
        peOrder: peOrder.data,
        ceStrike,
        peStrike,
        ceEntry: ceLtp,
        peEntry: peLtp,
        ceSL: (ceLtp * (1 + stopLoss/100)).toFixed(2),
        peSL: (peLtp * (1 + stopLoss/100)).toFixed(2),
        quantity,
        spotPrice
    };
}

async function executePremiumBasedStrangle(bridgeUrl, { underlying, expiry, lots, targetPremium, stopLoss }) {
    console.log(`Executing Premium Based Strangle for ${underlying}, Expiry: ${expiry}, Target: ${targetPremium}`);
    const strikesRes = await axios.get(`${bridgeUrl}/strikes`, { params: { symbol: underlying, expiry } });
    const strikes = strikesRes.data.strikes || [];
    const tokens = strikes.map(s => ({ instrument_token: s.pSymbol, exchange_segment: 'nse_fo' }));
    const quotesRes = await axios.post(`${bridgeUrl}/quotes`, { tokens });
    if (quotesRes.data.status !== 'success' || !quotesRes.data.data?.message) {
        throw new Error(quotesRes.data.message || "Failed to fetch quotes for strikes");
    }
    const quotes = quotesRes.data.data.message;
    let bestCE = null, bestPE = null, minCEDiff = Infinity, minPEDiff = Infinity;
    quotes.forEach(q => {
        const strikeInfo = strikes.find(s => s.pSymbol === q.instrument_token);
        if (!strikeInfo) return;
        const ltp = parseFloat(q.last_traded_price);
        const diff = Math.abs(ltp - targetPremium);
        if (strikeInfo.pOptionType === 'CE') { if (diff < minCEDiff) { minCEDiff = diff; bestCE = { ...strikeInfo, ltp }; } }
        else { if (diff < minPEDiff) { minPEDiff = diff; bestPE = { ...strikeInfo, ltp }; } }
    });
    if (!bestCE || !bestPE) throw new Error("Could not find suitable strikes for target premium");
    const lotSize = parseInt(bestCE.pLotSize) || (underlying === 'NIFTY' ? 65 : 20);
    const quantity = lots * lotSize;
    const ceOrder = await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: bestCE.pTrdSymbol, transaction_type: 'S', quantity, order_type: 'MKT' });
    const peOrder = await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: bestPE.pTrdSymbol, transaction_type: 'S', quantity, order_type: 'MKT' });

    if (stopLoss > 0) {
        const ceLtp = bestCE.ltp;
        const peLtp = bestPE.ltp;
        await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: bestCE.pTrdSymbol, transaction_type: 'B', quantity, order_type: 'SL-LMT', trigger_price: (ceLtp * (1 + stopLoss/100)).toFixed(2), price: (ceLtp * (1 + stopLoss/100) + 1).toFixed(2) });
        await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: bestPE.pTrdSymbol, transaction_type: 'B', quantity, order_type: 'SL-LMT', trigger_price: (peLtp * (1 + stopLoss/100)).toFixed(2), price: (peLtp * (1 + stopLoss/100) + 1).toFixed(2) });
    }

    return {
        status: 'success',
        ceOrder: ceOrder.data,
        peOrder: peOrder.data,
        ceStrike: bestCE,
        peStrike: bestPE,
        ceEntry: bestCE.ltp,
        peEntry: bestPE.ltp,
        ceSL: (bestCE.ltp * (1 + stopLoss/100)).toFixed(2),
        peSL: (bestPE.ltp * (1 + stopLoss/100)).toFixed(2),
        quantity
    };
}

async function executeSpotBasedStrangle(bridgeUrl, { underlying, expiry, lots, percentageOTM, stopLoss }) {
    console.log(`Executing Spot Based Strangle for ${underlying}, Expiry: ${expiry}, OTM%: ${percentageOTM}`);
    const spotRes = await axios.get(`${bridgeUrl}/spot`, { params: { symbol: underlying } });
    if (spotRes.data.status !== 'success' || !spotRes.data.quote?.message?.[0]) {
        throw new Error(spotRes.data.message || "Failed to fetch spot price");
    }
    const spotPrice = parseFloat(spotRes.data.quote.message[0].last_traded_price);
    const ceStrikePrice = spotPrice * (1 + percentageOTM / 100);
    const peStrikePrice = spotPrice * (1 - percentageOTM / 100);
    const strikesRes = await axios.get(`${bridgeUrl}/strikes`, { params: { symbol: underlying, expiry } });
    const strikes = strikesRes.data.strikes || [];

    const ceStrikes = strikes.filter(s => s.pOptionType === 'CE');
    const peStrikes = strikes.filter(s => s.pOptionType === 'PE');

    if (ceStrikes.length === 0 || peStrikes.length === 0) throw new Error("No strikes found for expiry");

    const ceStrike = ceStrikes.reduce((prev, curr) => Math.abs(parseFloat(curr.pStrikePrice) - ceStrikePrice) < Math.abs(parseFloat(prev.pStrikePrice) - ceStrikePrice) ? curr : prev);
    const peStrike = peStrikes.reduce((prev, curr) => Math.abs(parseFloat(curr.pStrikePrice) - peStrikePrice) < Math.abs(parseFloat(prev.pStrikePrice) - peStrikePrice) ? curr : prev);

    const lotSize = parseInt(ceStrike.pLotSize) || (underlying === 'NIFTY' ? 65 : 20);
    const quantity = lots * lotSize;
    const ceOrder = await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: ceStrike.pTrdSymbol, transaction_type: 'S', quantity, order_type: 'MKT' });
    const peOrder = await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: peStrike.pTrdSymbol, transaction_type: 'S', quantity, order_type: 'MKT' });

    // Fetch real-time quotes for entry prices and SL calculation
    const quotesRes = await axios.post(`${bridgeUrl}/quotes`, {
        tokens: [
            { instrument_token: ceStrike.pSymbol, exchange_segment: 'nse_fo' },
            { instrument_token: peStrike.pSymbol, exchange_segment: 'nse_fo' }
        ]
    });

    if (quotesRes.data.status !== 'success' || !quotesRes.data.data?.message) {
        throw new Error("Failed to fetch quotes for orders");
    }

    const quotes = quotesRes.data.data.message;
    const ceQuote = quotes.find(q => q.instrument_token === ceStrike.pSymbol);
    const peQuote = quotes.find(q => q.instrument_token === peStrike.pSymbol);

    if (!ceQuote || !peQuote) throw new Error("Quotes for placed orders not found");

    const ceLtp = parseFloat(ceQuote.last_traded_price);
    const peLtp = parseFloat(peQuote.last_traded_price);

    if (stopLoss > 0) {
        await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: ceStrike.pTrdSymbol, transaction_type: 'B', quantity, order_type: 'SL-LMT', trigger_price: (ceLtp * (1 + stopLoss/100)).toFixed(2), price: (ceLtp * (1 + stopLoss/100) + 1).toFixed(2) });
        await axios.post(`${bridgeUrl}/place_order`, { trading_symbol: peStrike.pTrdSymbol, transaction_type: 'B', quantity, order_type: 'SL-LMT', trigger_price: (peLtp * (1 + stopLoss/100)).toFixed(2), price: (peLtp * (1 + stopLoss/100) + 1).toFixed(2) });
    }

    return {
        status: 'success',
        ceOrder: ceOrder.data,
        peOrder: peOrder.data,
        ceStrike,
        peStrike,
        ceEntry: ceLtp,
        peEntry: peLtp,
        ceSL: (ceLtp * (1 + stopLoss/100)).toFixed(2),
        peSL: (peLtp * (1 + stopLoss/100)).toFixed(2),
        quantity,
        spotPrice
    };
}

module.exports = { executeShortStraddle, executePremiumBasedStrangle, executeSpotBasedStrangle };
