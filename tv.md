//@version=6
strategy("Volumatic Trend + OB Pro-Max 🚀", shorttitle="VolTrend+OB ProMax", overlay=true, max_bars_back=2000,
     pyramiding=0, initial_capital=10000, currency=currency.USD, commission_type=strategy.commission.percent, commission_value=0.03)

// —————————————————————————————————————————————————————————————————————————————
// 📌 User Inputs
// —————————————————————————————————————————————————————————————————————————————

// Trend Settings (Neon Theme)
volGroupTitle = "Volumatic Trend & Filters"
length = input.int(40, "Trend Length (EMA)", minval=1, group=volGroupTitle)
atr_period_trend = input.int(200, "ATR Period (Bands)", minval=10, group=volGroupTitle)
vol_h = input.bool(true, "Volume Histogram", group=volGroupTitle)
color_up = input.color(#00FFFF, "Up Trend (Neon Cyan)", group=volGroupTitle) // Neon Cyan
color_dn = input.color(#FF00FF, "Down Trend (Neon Fuchsia)", group=volGroupTitle) // Neon Fuchsia
use_filters = input.bool(true, "Use ALL Confirmation Filters", group=volGroupTitle, inline="filters")
// Filters
rsi_period = input.int(14, "RSI Period", minval=1, group=volGroupTitle, inline="filters")
rsi_overbought = input.int(70, "RSI Overbought", minval=50, maxval=100, group=volGroupTitle, inline="filters")
rsi_oversold = input.int(30, "RSI Oversold", minval=0, maxval=50, group=volGroupTitle, inline="filters")
vwap_band_multiplier = input.float(1.5, "VWAP Band Multiplier", minval=0.5, step=0.1, group=volGroupTitle)

// Order Block Settings
pivotGroupTitle = "Order Block Settings"
source_ob = input.string("Wicks", "OB Source", options=["Wicks", "Bodys"], group=pivotGroupTitle)
leftLen = input.int(25, "Pivot Left Bar Lookback", minval=1, group=pivotGroupTitle, inline="pivot")
rightLen = input.int(25, "Pivot Right Bar Lookforward", minval=0, group=pivotGroupTitle, inline="pivot")
bullBoxColor = input.color(color.new(#00FF00, 75), "Bull Color (Lime)", group=pivotGroupTitle)
bearBoxColor = input.color(color.new(#FF00FF, 75), "Bear Color (Fuchsia)", group=pivotGroupTitle)
closedBoxColor = input.color(color.new(color.gray, 85), "Closed Color", group=pivotGroupTitle)
extendBox = input.bool(true, "Extend Boxes", group=pivotGroupTitle)
max_boxes = input.int(50, "Max Boxes", minval=1, group=pivotGroupTitle)
min_ob_range = input.float(0.5, "Min OB Range (ATR Multiplier)", minval=0.1, step=0.1, group=pivotGroupTitle)
volume_ob_threshold = input.float(1.5, "Volume Spike Multiplier for OB", minval=1.0, step=0.1, group=pivotGroupTitle)

// Strategy & Risk Management
strategyGroupTitle = "Strategy & Risk Management"
use_strategy = input.bool(false, "Enable Strategy Mode (For Backtesting)", group=strategyGroupTitle)
risk_percent = input.float(1.0, "Risk % of Equity per Trade", minval=0.1, maxval=5.0, step=0.1, group=strategyGroupTitle)
risk_reward_ratio = input.float(1.5, "Take Profit / Stop Loss Ratio", minval=0.1, step=0.1, group=strategyGroupTitle)
atr_period_ce = input.int(14, "ATR Period (Chandelier Exit)", minval=1, group=strategyGroupTitle, inline="ce")
chandelier_multiplier = input.float(3.0, "Chandelier Multiplier", minval=0.1, step=0.1, group=strategyGroupTitle, inline="ce")
// Advanced Exit Management
use_trailing_stop = input.bool(true, "Use Trailing Stop (Chandelier Exit)", group=strategyGroupTitle, inline="adv_exit")
use_break_even = input.bool(true, "Use Break-Even Stop", group=strategyGroupTitle, inline="adv_exit")
break_even_level = input.float(1.0, "Break-Even at R:R Target", minval=0.5, step=0.1, group=strategyGroupTitle)
max_intraday_loss = input.float(5.0, "Max Intraday Loss % (Hard Stop)", minval=0.1, maxval=50.0, step=0.1, group=strategyGroupTitle)

// Time & Alert Filters
timeGroupTitle = "Time Filters & Alerts"
session_filter_text = input.session("0930-1600", "Trading Session", group=timeGroupTitle)
use_high_impact_time_filter = input.bool(false, "Filter 13:00 (High-Impact Time)", group=timeGroupTitle)
enable_alerts = input.bool(true, "Enable Alert Messages", group=timeGroupTitle)

// —————————————————————————————————————————————————————————————————————————————
// 📌 Indicator & Filter Calculations
// —————————————————————————————————————————————————————————————————————————————
// Trend
ema_swma(x, len) => ta.ema(x[3] * 1/6 + x[2] * 2/6 + x[1] * 2/6 + x[0] * 1/6, len)
atr_val = ta.atr(atr_period_trend)
ema1 = ema_swma(close, length)
ema2 = ta.ema(close, length)
trend = ema1 > ema2 // true for up trend

// Stop-Loss/Risk ATR
atr_ce = ta.atr(atr_period_ce)
chandelier_long = ta.highest(high, atr_period_ce) - (atr_ce * chandelier_multiplier)
chandelier_short = ta.lowest(low, atr_period_ce) + (atr_ce * chandelier_multiplier)

// Filters: RSI, MACD, VWAP, Session
rsi_val = ta.rsi(close, rsi_period)
rsi_filter = not use_filters or (trend ? rsi_val > rsi_oversold : rsi_val < rsi_overbought)
[macd_line, signal_line, _] = ta.macd(close, 12, 26, 9)
macd_filter = not use_filters or (trend ? macd_line > signal_line : macd_line < signal_line)

vwap_value = ta.vwap(hlc3)
vwap_upper = vwap_value + (atr_ce * vwap_band_multiplier)
vwap_lower = vwap_value - (atr_ce * vwap_band_multiplier)
vwap_filter = not use_filters or (close > vwap_lower and close < vwap_upper)

in_session = time(timeframe.period, session_filter_text)
is_high_impact_time = not use_high_impact_time_filter or (hour(time(timeframe.period)) != 13) // Filter out 13:00 news hour

// Combined Filter
all_filters_pass = rsi_filter and macd_filter and vwap_filter and not na(in_session) and is_high_impact_time

// Volume normalization (Cached for performance)
var float cached_percentile_vol = na
if ta.change(time("D")) or na(cached_percentile_vol)
    cached_percentile_vol := ta.percentile_linear_interpolation(volume, 1000, 100)
vol = int(nz(cached_percentile_vol) != 0 ? volume / cached_percentile_vol * 100 : 0)
volume_sma = ta.sma(volume, 20)
vol_spike = volume > volume_sma * volume_ob_threshold

// Trend Band Update & Alert
var float upper = na
var float lower = na
var int last_index = na
if trend != trend[1] and all_filters_pass
    upper := ema1 + atr_val * 3
    lower := ema1 - atr_val * 3
    last_index := bar_index
    if enable_alerts
        alert("Trend Change on " + syminfo.ticker + "! Direction: " + (trend ? "Bullish" : "Bearish"), alert.freq_once_per_bar_close)

// Volumetric Bands (Calculated after trend update)
vol_up = nz((lower + atr_val * 4 - lower) / 100 * vol)
vol_dn = nz((upper - (upper - atr_val * 4)) / 100 * vol)

// Color calculations
trend_color = trend ? color_up : color_dn
grad_col = color.from_gradient(vol, 0, 25, chart.bg_color, trend_color)
grad_col1 = color.from_gradient(vol, 0, 10, chart.bg_color, trend_color)
col_vol_up = trend ? grad_col : na
col_vol_dn = not trend ? grad_col : na

// —————————————————————————————————————————————————————————————————————————————
// 📌 Pivot Order Blocks
// —————————————————————————————————————————————————————————————————————————————
phOption = source_ob == "Wicks" ? high : close
plOption = source_ob == "Wicks" ? low : close
ph = ta.pivothigh(phOption, leftLen, rightLen)
pl = ta.pivotlow(plOption, leftLen, rightLen)

// Box arrays
var box[] bullBoxes = array.new_box(0)
var box[] bearBoxes = array.new_box(0)

// Function to create and manage boxes (simplified and more efficient)
create_box(is_bull, pivot_price, pivot_index) =>
    right_len_lookback = is_bull ? rightLen : rightLen
    left_len_lookback = is_bull ? leftLen : leftLen
    
    // Determine the candle that created the pivot for OB bounds
    ob_idx = bar_index - right_len_lookback
    
    // Define the price range of the order block candle
    top_price = is_bull ? math.max(close[right_len_lookback], open[right_len_lookback]) : high[right_len_lookback]
    bottom_price = is_bull ? low[right_len_lookback] : math.min(close[right_len_lookback], open[right_len_lookback])
    
    // Ensure top > bottom
    if top_price < bottom_price
        [top_price, bottom_price] = [bottom_price, top_price]
        
    range_atr = (top_price - bottom_price) / atr_ce
    
    if range_atr >= min_ob_range and vol_spike and all_filters_pass
        new_box = box.new(left=ob_idx, right=ob_idx + 1, 
             top=top_price, bottom=bottom_price, 
             bgcolor=color.new(is_bull ? bullBoxColor : bearBoxColor, 70), 
             border_color=is_bull ? bullBoxColor : bearBoxColor, extend=extend.none)
        
        array_push(is_bull ? bullBoxes : bearBoxes, new_box)
        
        if enable_alerts
            alert_msg = (is_bull ? "Bullish" : "Bearish") + " OB Created (Vol Spike) on " + syminfo.ticker
            alert(alert_msg, alert.freq_once_per_bar_close)

// Create boxes
if not na(ph)
    create_box(false, ph, rightLen)
if not na(pl)
    create_box(true, pl, rightLen)

// Box management function (Check for touch/closure and extend)
manage_boxes(boxes, is_bull) =>
    var float touch_price = na
    i = array.size(boxes) - 1
    while i >= 0
        box = array.get(boxes, i)
        box_top = box.get_top(box)
        box_bottom = box.get_bottom(box)
        
        // Closure condition: price closes entirely outside the block in the opposite direction
        closed_cond = is_bull ? close < box_bottom : close > box_top
        
        // Touch condition: price interacts with the block without closing it
        touched_cond = (high >= box_bottom and low <= box_top)
        
        if closed_cond
            box.set_bgcolor(box, closedBoxColor)
            box.set_border_color(box, closedBoxColor)
            box.set_right(box, bar_index)
            if enable_alerts and na(touch_price)
                touch_price := is_bull ? box_bottom : box_top
                alert_msg = (is_bull ? "Bullish" : "Bearish") + " OB Closed/Invalidated on " + syminfo.ticker
                alert(alert_msg, alert.freq_once_per_bar_close)
            
            // Remove closed/invalidated boxes to keep the array clean and only contain active/extended
            box.delete(array.remove(boxes, i)) 
        else
            if extendBox
                box.set_right(box, bar_index + 1)
            
            if touched_cond and enable_alerts and na(touch_price) and box.get_right(box) == bar_index + 1 // Only alert if active
                touch_price := is_bull ? box_bottom : box_top
                alert_msg = (is_bull ? "Bullish" : "Bearish") + " OB Touched/Re-tested on " + syminfo.ticker
                alert(alert_msg, alert.freq_once_per_bar_close)
            i := i - 1

manage_boxes(bullBoxes, true)
manage_boxes(bearBoxes, false)

// Clean up old boxes (only needed for *active* boxes if closure logic above is not used to remove them)
while array.size(bullBoxes) > max_boxes
    box.delete(array.shift(bullBoxes))
while array.size(bearBoxes) > max_boxes
    box.delete(array.shift(bearBoxes))

// —————————————————————————————————————————————————————————————————————————————
// 📌 Strategy Logic
// —————————————————————————————————————————————————————————————————————————————
if use_strategy

    // Daily Loss Limit Check
    var float daily_high_equity = strategy.initial_capital
    if ta.change(time("D"))
        daily_high_equity := strategy.equity
    daily_high_equity := math.max(daily_high_equity, strategy.equity)
    daily_drawdown = ((daily_high_equity - strategy.equity) / daily_high_equity) * 100
    max_daily_loss_reached = daily_drawdown >= max_intraday_loss

    // Trade Sizing (Risk % of Equity / ATR Stop Distance)
    risk_dollars = strategy.equity * (risk_percent / 100)
    
    // Check for the most recent active OB (last item in array)
    last_bull_ob_bottom = array.size(bullBoxes) > 0 ? array.get(bullBoxes, array.size(bullBoxes) - 1).get_bottom() : na
    last_bear_ob_top = array.size(bearBoxes) > 0 ? array.get(bearBoxes, array.size(bearBoxes) - 1).get_top() : na

    // Entry Conditions: Trend + All Filters + Price in/touching the last active OB
    long_entry_cond = trend and all_filters_pass and not max_daily_loss_reached and high >= last_bull_ob_bottom and low <= last_bull_ob_bottom
    short_entry_cond = not trend and all_filters_pass and not max_daily_loss_reached and low <= last_bear_ob_top and high >= last_bear_ob_top

    if long_entry_cond and strategy.position_size == 0
        sl_price = chandelier_long
        risk_distance = close - sl_price
        tp_price = close + risk_distance * risk_reward_ratio
        
        // Calculate position size based on risk and stop distance
        position_size = math.round(risk_dollars / risk_distance)
        if position_size > 0 and not na(sl_price)
            strategy.entry("Long", strategy.long, qty=position_size, comment="Long Entry")
            strategy.exit("Long Exit", from_entry="Long", stop=sl_price, limit=tp_price, comment="Long TP/SL")
            if enable_alerts
                alert("LONG ENTRY on " + syminfo.ticker + "! Qty: " + str.tostring(position_size), alert.freq_once_per_bar_close)

    if short_entry_cond and strategy.position_size == 0
        sl_price = chandelier_short
        risk_distance = sl_price - close
        tp_price = close - risk_distance * risk_reward_ratio
        
        // Calculate position size based on risk and stop distance
        position_size = math.round(risk_dollars / risk_distance)
        if position_size > 0 and not na(sl_price)
            strategy.entry("Short", strategy.short, qty=position_size, comment="Short Entry")
            strategy.exit("Short Exit", from_entry="Short", stop=sl_price, limit=tp_price, comment="Short TP/SL")
            if enable_alerts
                alert("SHORT ENTRY on " + syminfo.ticker + "! Qty: " + str.tostring(position_size), alert.freq_once_per_bar_close)

    // Advanced Exit Management
    // Trailing Stop (Chandelier Exit overrides other exits)
    var float current_stop = na
    if strategy.position_size > 0 and use_trailing_stop
        current_stop := math.max(nz(current_stop[1], chandelier_long), chandelier_long)
        strategy.exit("Long Trailing", from_entry="Long", stop=current_stop, comment="TSL")

    if strategy.position_size < 0 and use_trailing_stop
        current_stop := math.min(nz(current_stop[1], chandelier_short), chandelier_short)
        strategy.exit("Short Trailing", from_entry="Short", stop=current_stop, comment="TSS")

    // Break-Even Logic (Adjusts SL to entry price once R:R target is hit)
    // The previous exit needs to be cancelled/modified. strategy.exit() can modify existing orders by using the same `id`.
    if strategy.position_size > 0 and use_break_even and strategy.opentrades.entry_price(strategy.opentrades - 1) != na
        entry_price = strategy.opentrades.entry_price(strategy.opentrades - 1)
        risk_distance = entry_price - chandelier_long
        if close >= entry_price + risk_distance * break_even_level
            strategy.exit("Long Exit", from_entry="Long", stop=entry_price, limit=tp_price, comment="Long BE/TP")
            if enable_alerts and strategy.exit.id(strategy.opentrades.exit_id(strategy.opentrades - 1)) != "Long BE/TP"
                alert("LONG Stop Moved to Break-Even on " + syminfo.ticker, alert.freq_once_per_bar_close)

    if strategy.position_size < 0 and use_break_even and strategy.opentrades.entry_price(strategy.opentrades - 1) != na
        entry_price = strategy.opentrades.entry_price(strategy.opentrades - 1)
        risk_distance = chandelier_short - entry_price
        if close <= entry_price - risk_distance * break_even_level
            strategy.exit("Short Exit", from_entry="Short", stop=entry_price, limit=tp_price, comment="Short BE/TP")
            if enable_alerts and strategy.exit.id(strategy.opentrades.exit_id(strategy.opentrades - 1)) != "Short BE/TP"
                alert("SHORT Stop Moved to Break-Even on " + syminfo.ticker, alert.freq_once_per_bar_close)
    
    // Daily Loss Limit Hard Close
    if max_daily_loss_reached and strategy.position_size != 0
        strategy.close_all("Daily Loss Limit Reached")
        if enable_alerts
            alert("ALL POSITIONS CLOSED - Daily loss limit reached on " + syminfo.ticker, alert.freq_once_per_bar_close)

// —————————————————————————————————————————————————————————————————————————————
// 📌 Visualizations
// —————————————————————————————————————————————————————————————————————————————
// Volumatic Trend Visualization
plotcandle(open, high, low, close, title='Volumatic Candles', color=grad_col1, wickcolor=grad_col1, bordercolor=grad_col1)
plotcandle(lower, lower, lower + vol_up, lower + vol_up, 'Volume Up Trend', color=col_vol_up, wickcolor=col_vol_up, bordercolor=col_vol_up, display=vol_h ? display.all : display.none)
plotcandle(upper, upper, upper - vol_dn, upper - vol_dn, 'Volume Down Trend', color=col_vol_dn, wickcolor=col_vol_dn, bordercolor=col_vol_dn, display=vol_h ? display.all : display.none)
plot(upper, color=trend_color, style=plot.style_linebr, linewidth=1)
plot(lower, color=trend_color, style=plot.style_linebr, linewidth=1)
plot(ema1, "Trend Line", color=color.new(trend_color, 20), linewidth=2)
plotshape(trend != trend[1] ? ema1[1] : na, "Trend Change", style=shape.diamond, location=location.absolute, color=trend_color, size=size.tiny, offset=-1)

// VWAP Visualization (Neon Purple)
vwap_color = color.new(#A020F0, 0)
plot(vwap_value, "VWAP", color=vwap_color, linewidth=1)
plot(vwap_upper, "VWAP Upper Band", color=color.new(vwap_color, 70), linewidth=1, style=plot.style_line)
plot(vwap_lower, "VWAP Lower Band", color=color.new(vwap_color, 70), linewidth=1, style=plot.style_line)

// Background Highlights
bgcolor(trend ? color.new(color_up, 95) : color.new(color_dn, 95), title="Trend Background")
bgcolor(not na(in_session) and not in_session ? color.new(color.gray, 90) : na, title="Off-Session Highlight")
bgcolor(use_high_impact_time_filter and not is_high_impact_time ? color.new(color.orange, 90) : na, title="High-Impact Time Highlight")
bgcolor(use_strategy and max_daily_loss_reached ? color.new(color.red, 90) : na, title="Daily Loss Limit Reached")
