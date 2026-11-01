package com.indirimde.app.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.indirimde.app.AppViewModel
import com.indirimde.app.core.Money
import com.indirimde.app.data.Product
import com.indirimde.app.data.Watch

@Composable
fun AppScreen(vm: AppViewModel) {
    var tab by rememberSaveable { mutableStateOf(0) }

    Box(
        Modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(FrostTop, FrostBottom)))
    ) {
        Column(Modifier.fillMaxSize().padding(horizontal = 18.dp)) {
            Spacer(Modifier.height(22.dp))
            Text("indirimde", fontSize = 30.sp, fontWeight = FontWeight.Bold, color = Ink)
            Text(
                "Takip et, düşünce haber ver",
                fontSize = 14.sp, color = Ink2, modifier = Modifier.padding(top = 2.dp)
            )
            Spacer(Modifier.height(16.dp))

            Segmented(tab) { tab = it }
            Spacer(Modifier.height(14.dp))

            if (tab == 0) SearchTab(vm) else WatchTab(vm)
        }
    }
}

@Composable
private fun Segmented(selected: Int, onSelect: (Int) -> Unit) {
    val labels = listOf("Ara", "Takip")
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = Color(0x0F1C1C1E),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(Modifier.padding(4.dp)) {
            labels.forEachIndexed { i, label ->
                val on = i == selected
                Box(
                    Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(11.dp))
                        .background(if (on) Color.White else Color.Transparent)
                        .clickable { onSelect(i) }
                        .padding(vertical = 9.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        label,
                        color = if (on) Blue else Ink2,
                        fontWeight = if (on) FontWeight.SemiBold else FontWeight.Medium
                    )
                }
            }
        }
    }
}

@Composable
private fun SearchTab(vm: AppViewModel) {
    Column(Modifier.fillMaxSize()) {
        OutlinedTextField(
            value = vm.query,
            onValueChange = vm::onQueryChange,
            placeholder = { Text("Ürün ara (ör. kulaklık)") },
            leadingIcon = { Icon(Icons.Rounded.Search, null, tint = Ink2) },
            singleLine = true,
            shape = RoundedCornerShape(14.dp),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = Color.White,
                unfocusedContainerColor = GlassWhite,
                focusedIndicatorColor = Blue,
                unfocusedIndicatorColor = GlassHairline,
            ),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            keyboardActions = KeyboardActions(onSearch = { vm.search() }),
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(Modifier.height(12.dp))

        if (vm.searching) {
            CenterBusy("Trendyol aranıyor…")
        } else if (vm.searchError != null && vm.results.isEmpty()) {
            CenterNote(vm.searchError!!)
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                contentPadding = PaddingValues(bottom = 24.dp)
            ) {
                items(vm.results, key = { it.key }) { p ->
                    ResultCard(p, watched = vm.isWatched(p)) { vm.addWatch(p) }
                }
            }
        }
    }
}

@Composable
private fun WatchTab(vm: AppViewModel) {
    Column(Modifier.fillMaxSize()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                if (vm.watches.isEmpty()) "Takip listen boş"
                else "${vm.watches.size} ürün takipte",
                color = Ink2, modifier = Modifier.weight(1f)
            )
            Button(
                onClick = vm::checkNow,
                enabled = !vm.checking && vm.watches.isNotEmpty(),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Blue)
            ) { Text(if (vm.checking) "Kontrol ediliyor…" else "Şimdi kontrol et") }
        }
        Spacer(Modifier.height(12.dp))

        if (vm.watches.isEmpty()) {
            CenterNote("\"Ara\" sekmesinden ürün ekle.")
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                contentPadding = PaddingValues(bottom = 24.dp)
            ) {
                items(vm.watches, key = { it.product.key }) { w ->
                    WatchCard(w) { vm.removeWatch(w.product.key) }
                }
            }
        }
    }
}

@Composable
private fun GlassCard(content: @Composable () -> Unit) {
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = GlassWhite,
        border = BorderStroke(1.dp, GlassHairline),
        shadowElevation = 6.dp,
        modifier = Modifier.fillMaxWidth()
    ) { Box(Modifier.padding(12.dp)) { content() } }
}

@Composable
private fun ResultCard(p: Product, watched: Boolean, onAdd: () -> Unit) {
    GlassCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            ProductImage(p.image)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                if (p.brand.isNotBlank())
                    Text(p.brand, color = Ink2, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                Text(p.name, color = Ink, maxLines = 2, overflow = TextOverflow.Ellipsis, fontSize = 14.sp)
                Spacer(Modifier.height(4.dp))
                PriceLine(p.saleMinor, p.wasMinor, p.currency)
            }
            Spacer(Modifier.width(8.dp))
            if (watched) {
                Text("Takipte", color = Green, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
            } else {
                TextButton(onClick = onAdd) { Text("Takip et", color = Blue, fontWeight = FontWeight.SemiBold) }
            }
        }
    }
}

@Composable
private fun WatchCard(w: Watch, onRemove: () -> Unit) {
    GlassCard {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                ProductImage(w.product.image)
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text(w.product.name, color = Ink, maxLines = 2, overflow = TextOverflow.Ellipsis, fontSize = 14.sp)
                    Spacer(Modifier.height(4.dp))
                    val current = w.baselineMinor ?: w.addedMinor
                    PriceLine(current, w.product.wasMinor, w.currency)
                }
                Spacer(Modifier.width(8.dp))
                StatusChip(w)
            }
            Spacer(Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "Eklendiğinde: ${Money(w.addedMinor, w.currency).format()}",
                    color = Ink2, fontSize = 12.sp, modifier = Modifier.weight(1f)
                )
                TextButton(onClick = onRemove) { Text("Kaldır", color = Red) }
            }
        }
    }
}

@Composable
private fun StatusChip(w: Watch) {
    val base = w.baselineMinor
    val (label, color) = when {
        !w.lastReachable -> "ulaşılamadı" to Amber
        base == null -> "ilk kontrol" to Gray
        base < w.addedMinor -> "düştü" to Green
        base > w.addedMinor -> "arttı" to Red
        else -> "aynı" to Gray
    }
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(color))
        Spacer(Modifier.width(6.dp))
        Text(label, color = Ink2, fontSize = 12.sp, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun PriceLine(saleMinor: Long, wasMinor: Long?, currency: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            Money(saleMinor, currency).format(),
            color = Ink, fontWeight = FontWeight.Bold, fontSize = 16.sp
        )
        if (wasMinor != null && wasMinor > saleMinor) {
            Spacer(Modifier.width(8.dp))
            Text(
                Money(wasMinor, currency).format(),
                color = Gray, fontSize = 13.sp,
                textDecoration = TextDecoration.LineThrough
            )
        }
    }
}

@Composable
private fun ProductImage(url: String) {
    Surface(shape = RoundedCornerShape(12.dp), color = Color(0x0F1C1C1E)) {
        AsyncImage(
            model = url,
            contentDescription = null,
            modifier = Modifier.size(60.dp).clip(RoundedCornerShape(12.dp))
        )
    }
}

@Composable
private fun CenterBusy(text: String) {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(color = Blue)
            Spacer(Modifier.height(12.dp))
            Text(text, color = Ink2)
        }
    }
}

@Composable
private fun CenterNote(text: String) {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Text(text, color = Ink2)
    }
}
