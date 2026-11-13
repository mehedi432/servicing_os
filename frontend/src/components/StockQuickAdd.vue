<script setup>
import {ref,computed,onBeforeUnmount} from 'vue'
import {shopApi} from './shopQuickApi.js'
const emit=defineEmits(['changed'])
const opened=ref(false),tab=ref('add'),loading=ref(false),saving=ref(false),error=ref(''),success=ref('')
const setup=ref({warehouses:[],groups:[],uoms:[],brands:[],suppliers:[]})
const product=ref({item_name:'',item_code:'',item_group:'',stock_uom:'Nos',brand:'',barcode:'',warranty_period:'',selling_price:'',has_serial_no:false})
const receipt=ref({item_code:'',warehouse:'Stores - AMCL',supplier:'',qty:1,rate:'',serial_numbers:''})
const prodQuery=ref(''),matches=ref([]),picked=ref(null),searching=ref(false),draft=ref(null)
const showSupplier=ref(false),supplierForm=ref({supplier_name:'',supplier_group:'',supplier_type:'Company'})
let searchTimer=null,requestId=0
const serialList=computed(()=>receipt.value.serial_numbers.split(/[\r\n,]+/).map(s=>s.trim()).filter(Boolean))
const receiptTotal=computed(()=>Number(receipt.value.qty||0)*Number(receipt.value.rate||0))
const money=n=>'৳'+Number(n||0).toLocaleString('en-BD',{minimumFractionDigits:2,maximumFractionDigits:2})
function resetErrors(){error.value='';success.value=''}
async function load(){loading.value=true;resetErrors();try{
  const r=await shopApi('get_product_setup');setup.value=r;
  if(!r.warehouses.includes(receipt.value.warehouse))receipt.value.warehouse=r.warehouses[0]||''
  if(!r.uoms.includes(product.value.stock_uom))product.value.stock_uom=r.uoms[0]||'Nos'
  if(!supplierForm.value.supplier_group)supplierForm.value.supplier_group=(r.supplier_groups||[])[0]||''
}catch(e){error.value=e.message}finally{loading.value=false}}
async function open(mode='add'){tab.value=mode;opened.value=true;draft.value=null;await load()}
function close(){if(!saving.value){opened.value=false;requestId++;clearTimeout(searchTimer)}}
function selectItem(i){picked.value=i;receipt.value.item_code=i.name;prodQuery.value=i.item_name+' · '+i.name;matches.value=[];receipt.value.qty=1;receipt.value.serial_numbers='';draft.value=null}
function newSearch(){requestId++;clearTimeout(searchTimer);picked.value=null;receipt.value.item_code='';draft.value=null;let q=prodQuery.value.trim();if(q.length<2){matches.value=[];return}
const seq=++requestId;searchTimer=setTimeout(async()=>{searching.value=true;try{let r=await shopApi('find_products',{search:q});if(seq===requestId)matches.value=r.items||[]}catch(e){if(seq===requestId)error.value=e.message}finally{if(seq===requestId)searching.value=false}},240)}
async function makeSupplier(){resetErrors();saving.value=true;try{
   const result=await shopApi('create_supplier',{data:supplierForm.value},true)
   setup.value.suppliers=[...setup.value.suppliers,result]
   receipt.value.supplier=result.name;showSupplier.value=false
   success.value=`Supplier ${result.supplier_name} added and selected.`
   supplierForm.value.supplier_name=''
 }catch(e){error.value=e.message}finally{saving.value=false}}
async function makeProduct(){resetErrors();if(!setup.value.can_create_item){error.value='Your account does not have permission to create products.';return}
  if(!product.value.item_name.trim() || !product.value.item_group || !product.value.stock_uom){error.value='Enter name, product group and unit.';return}
  saving.value=true;try{
    const out=await shopApi('create_product',{data:product.value},true)
    success.value=`${out.item_name} created. Stock is still zero; receive actual units next.`
    selectItem({name:out.item_code,item_name:out.item_name,has_serial_no:out.serialized})
    receipt.value.warehouse=setup.value.warehouses.includes('Stores - AMCL')?'Stores - AMCL':(setup.value.warehouses[0]||'')
    product.value={item_name:'',item_code:'',item_group:'',stock_uom:'Nos',brand:'',barcode:'',warranty_period:'',selling_price:'',has_serial_no:false}
    tab.value='receive';emit('changed')
  }catch(e){error.value=e.message}finally{saving.value=false}}
async function saveDraft(){resetErrors();if(!picked.value){error.value='Search and select a product first.';return}
  const qty=Number(receipt.value.qty);if(!(qty>=1) || !Number.isFinite(qty)){error.value='Enter a valid quantity.';return}
  if(receipt.value.rate===''||Number(receipt.value.rate)<0){error.value='Enter the actual purchase rate per unit.';return}
  if(picked.value.has_serial_no && (Math.floor(qty)!==qty || serialList.value.length!==qty || (new Set(serialList.value)).size!==qty)){
    error.value='Enter a unique physical serial number on its own line for EVERY unit.';return
  }
  if(!picked.value.has_serial_no && serialList.value.length){error.value='This product was not created as serial-tracked.';return}
  saving.value=true;try{
    draft.value=await shopApi('create_receipt_draft',{data:{...receipt.value,serial_numbers:serialList.value}},true)
    success.value=`Draft ${draft.value.receipt} saved. Stock has NOT been received yet.`
    emit('changed')
  }catch(e){error.value=e.message}finally{saving.value=false}}
async function confirmReceive(){resetErrors();if(!draft.value)return
  if(!window.confirm(`Confirm physical receipt ${draft.value.receipt}? This will post ${draft.value.qty} unit(s) into ${receipt.value.warehouse} and affect real stock and accounting.`))return
  saving.value=true;try{
    const out=await shopApi('confirm_receipt',{receipt:draft.value.receipt},true)
    success.value=`Received successfully: ${out.receipt}. Stock ledger updated.`
    draft.value={...draft.value,docstatus:1}
    emit('changed')
  }catch(e){error.value=e.message+' Your draft is preserved; no successful stock posting was reported.'}finally{saving.value=false}}
onBeforeUnmount(()=>{requestId++;clearTimeout(searchTimer)})
</script>
<template>
  <div class="si-wrap">
    <button class="si-launch" type="button" @click="open('add')"><span>＋</span> Add New Item</button>
    <button class="si-launch si-outline" type="button" @click="open('receive')">↓ Receive Stock</button>
    <div v-if="opened" class="si-backdrop" @click.self="close">
      <div class="si-modal" role="dialog" aria-modal="true" aria-label="Add product or receive stock">
        <div class="si-top"><div><small>INVENTORY / QUICK ACTION</small><h2>Add New Item / Receive Stock</h2><p>One form at a time. Exact item details and physical serial numbers.</p></div><button type="button" class="si-x" @click="close" :disabled="saving">×</button></div>
        <div class="si-tabs"><button type="button" :class="{on:tab==='add'}" @click="tab='add';resetErrors()">1 · Add New Item</button><button type="button" :class="{on:tab==='receive'}" @click="tab='receive';resetErrors()">2 · Receive Stock</button></div>
        <div v-if="loading" class="si-status">Loading shop configuration…</div>
        <div v-if="error" class="si-error" role="alert">{{error}}</div>
        <div v-if="success" class="si-success" role="status">{{success}}</div>
        <form v-if="tab==='add'" class="si-form" @submit.prevent="makeProduct">
          <div class="si-grid">
            <label class="si-wide">Product Name <b>*</b><input v-model="product.item_name" required placeholder="e.g. Samsung 980 1TB NVMe SSD" maxlength="140" /></label>
            <label>Item Code / SKU<input v-model="product.item_code" placeholder="Leave blank to use name" maxlength="140"/></label>
            <label>Item Group <b>*</b><select v-model="product.item_group" required><option value="">Select Group</option><option v-for="g in setup.groups" :key="g">{{g}}</option></select></label>
            <label>Stock Unit <b>*</b><select v-model="product.stock_uom" required><option v-for="u in setup.uoms" :key="u">{{u}}</option></select></label>
            <label>Brand<select v-model="product.brand"><option value="">No brand</option><option v-for="b in setup.brands" :key="b">{{b}}</option></select></label>
            <label>Barcode / UPC<input v-model="product.barcode" placeholder="Optional scanner barcode" maxlength="100"/></label>
            <label>Warranty (months)<input v-model="product.warranty_period" type="number" min="0" max="120" step="1" placeholder="Optional"/></label>
            <label>Selling Price (BDT)<input v-model="product.selling_price" type="number" min="0" step="0.01" placeholder="Optional; not purchase cost"/></label>
          </div>
          <label class="si-check"><input v-model="product.has_serial_no" type="checkbox"/><span><strong>Track a separate serial number for each unit</strong><small>Use for laptops, desktops, monitors, SSDs with individual warranty / tracking. Cannot change after stock transactions.</small></span></label>
          <div class="si-foot"><span>Creating a Product alone does not add stock.</span><button class="si-primary" type="submit" :disabled="saving||loading||!setup.can_create_item">{{saving?'Creating…':'Create Product & Continue →'}}</button></div>
          <p v-if="!setup.can_create_item" class="si-note">This login cannot create Items. Ask an administrator for Item Create permission.</p>
        </form>
        <div v-else class="si-form">
          <div v-if="!draft" class="si-grid">
            <label class="si-wide si-search">Product <b>*</b><input v-model="prodQuery" @input="newSearch" placeholder="Start typing item name or code…" autocomplete="off"/><span v-if="searching" class="si-search-state">Finding products…</span>
              <div v-if="matches.length" class="si-matches"><button v-for="i in matches" :key="i.name" type="button" @click="selectItem(i)"><strong>{{i.item_name}}</strong><small>{{i.name}} · {{i.has_serial_no?'Serial-tracked':'Regular stock'}}</small></button></div>
              <span v-if="picked" class="si-picked">✓ Selected: {{picked.name}}</span>
            </label>
            <label>Receive to Warehouse <b>*</b><select v-model="receipt.warehouse"><option v-for="w in setup.warehouses" :key="w">{{w}}</option></select></label>
            <label>Supplier <b>*</b><select v-model="receipt.supplier"><option value="">Choose supplier</option><option v-for="s in setup.suppliers" :key="s.name" :value="s.name">{{s.supplier_name||s.name}}</option></select></label>
            <div class="si-wide si-supplier-add"><button v-if="setup.can_create_supplier" type="button" class="si-tiny" @click="showSupplier=!showSupplier">{{showSupplier?'Cancel New Supplier':'＋ Add Supplier Without Leaving This Screen'}}</button>
              <form v-if="showSupplier" class="si-supplier-box" @submit.prevent="makeSupplier">
                <label>Supplier Name <input v-model="supplierForm.supplier_name" required minlength="2" maxlength="140" placeholder="Supplier or seller name" /></label>
                <label>Supplier Group <select v-model="supplierForm.supplier_group" required><option value="">Select group</option><option v-for="g in setup.supplier_groups||[]" :key="g">{{g}}</option></select></label>
                <label>Type <select v-model="supplierForm.supplier_type"><option>Company</option><option>Individual</option></select></label>
                <button type="submit" class="si-tiny si-tiny-solid" :disabled="saving || !supplierForm.supplier_name || !supplierForm.supplier_group">{{saving?'Saving…':'Save & Select Supplier'}}</button>
              </form>
            </div>
            <label>Quantity <b>*</b><input v-model.number="receipt.qty" type="number" :step="picked?.has_serial_no?1:0.001" min="1" max="100000"/></label>
            <label>Actual Purchase Rate / Unit <b>*</b><input v-model="receipt.rate" type="number" step="0.01" min="0" placeholder="Supplier buying rate in BDT"/></label>
            <label v-if="picked?.has_serial_no" class="si-wide">Physical Serial Numbers <b>*</b><textarea v-model="receipt.serial_numbers" rows="5" placeholder="Enter or scan one real serial number per line"></textarea><small>{{serialList.length}} of {{receipt.qty||0}} serials entered. Every unit must have a unique serial number.</small></label>
          </div>
          <div v-if="draft" class="si-review"><strong>Draft Receipt: {{draft.receipt}}</strong><p>{{draft.qty}} × {{draft.item_code}} · {{draft.serial_count}} serial numbers · {{draft.docstatus===1?'Submitted / Stock received':'DRAFT / NO STOCK POSTED'}}</p><p>For physical stock to increase, confirm the actual goods below.</p></div>
          <div class="si-foot"><span>{{draft?'Receipt is saved, but not posted until confirmed.':'Estimated purchase value: '+money(receiptTotal)}}</span>
            <button v-if="!draft" class="si-primary" type="button" :disabled="saving||loading||!setup.can_create_receipt" @click="saveDraft">{{saving?'Saving…':'Save Stock Receipt Draft'}}</button>
            <button v-else-if="draft.docstatus!==1" class="si-primary" type="button" :disabled="saving||!setup.can_submit_receipt" @click="confirmReceive">{{saving?'Posting…':'✓ Confirm Received Stock'}}</button>
            <button v-else class="si-primary" type="button" @click="draft=null;receipt.serial_numbers='';picked=null;receipt.item_code='';prodQuery=''">Receive Another</button></div>
          <p v-if="!setup.can_create_receipt" class="si-note">Creating receipts requires Purchase Receipt Create permission.</p>
          <p v-else-if="draft?.docstatus!==1&&!setup.can_submit_receipt" class="si-note">Receipt submission requires Submit permission. An authorized manager must confirm.</p>
          <p class="si-note">Serial numbers are stored with the stock receipt and checked again by the native serial ledger when received. If that validation fails, the draft stays unposted.</p>
        </div>
      </div>
    </div>
  </div>
</template>
<style scoped>
.si-wrap{display:flex;justify-content:flex-start;gap:9px;flex-wrap:wrap;margin:0 0 16px}.si-launch{border:1px solid #836646;background:#755a3e;color:white;padding:12px 16px;font-size:12px;font-weight:850;cursor:pointer;border-radius:12px}.si-launch span{font-size:18px;line-height:0}.si-outline{background:white;color:#765a3f;border-color:#dfceba}.si-backdrop{position:fixed;inset:0;z-index:100000;background:#251c15a3;display:flex;align-items:center;justify-content:center;padding:12px;overflow:auto}.si-modal{font-family:inherit;color:#43392e;background:#fffdfa;border-radius:22px;width:min(780px,100%);box-shadow:0 22px 80px #21190f40;max-height:min(92vh,900px);overflow-y:auto;padding:24px;box-sizing:border-box}.si-modal *{box-sizing:border-box}.si-top{display:flex;align-items:flex-start;gap:16px;justify-content:space-between}.si-top small{font-size:10px;letter-spacing:.12em;font-weight:850;color:#a1896b}.si-top h2{margin:7px 0;font-size:23px;font-weight:800}.si-top p{margin:0;color:#8d7a61;font-size:12px}.si-x{cursor:pointer;border:1px solid #e4d8c9;border-radius:11px;font-size:25px;width:36px;height:36px;background:white;color:#86745f}.si-tabs{display:flex;gap:9px;border-bottom:1px solid #ede3d6;margin:18px 0;padding-bottom:11px}.si-tabs button{border:1px solid #e8ded1;border-radius:10px;background:#f6f2ec;color:#8a765e;padding:11px 14px;font-weight:800;font-size:12px;cursor:pointer}.si-tabs button.on{background:#70563d;color:white;border-color:#70563d}.si-form{padding:0}.si-grid{display:grid;grid-template-columns:1fr 1fr;gap:13px}.si-grid label{display:flex;flex-direction:column;gap:7px;font-size:12px;font-weight:760;position:relative}.si-grid label b{color:#aa6b3b}.si-grid .si-wide{grid-column:1 / -1}.si-grid input,.si-grid select,.si-grid textarea{outline:0;border:1px solid #dfd4c6;border-radius:10px;min-width:0;font:inherit;font-size:13px;background:white;color:#4e4032;padding:12px}.si-grid input:focus,.si-grid select:focus,.si-grid textarea:focus{border-color:#a78b67;box-shadow:0 0 0 3px #e8d6be7a}.si-grid textarea{resize:vertical;font-family:ui-monospace,monospace}.si-grid label small{font-size:11px;color:#96846b;font-weight:400}.si-check{display:flex;gap:12px;background:#f5efe5;border:1px solid #e8d9c6;padding:14px;margin-top:16px;border-radius:12px;align-items:flex-start}.si-check input{margin-top:3px;width:18px;height:18px}.si-check span{display:grid;gap:5px}.si-check strong{font-size:12px}.si-check small{font-size:11px;color:#8d7e68}.si-foot{display:flex;justify-content:space-between;align-items:center;gap:12px;border-top:1px solid #eee5d8;margin-top:19px;padding-top:17px}.si-foot span{font-size:11px;color:#8b7c6a}.si-primary{border:0;border-radius:11px;background:#70553a;color:white;font-size:12px;font-weight:850;padding:13px 18px;cursor:pointer;white-space:nowrap}.si-primary:disabled{opacity:.45;cursor:not-allowed}.si-error,.si-success,.si-status{padding:11px 13px;border-radius:10px;font-size:12px;margin:12px 0}.si-error{color:#933a25;background:#fff0e8}.si-success{color:#346a42;background:#eaf6e9}.si-status{background:#f4eee2}.si-note{font-size:11px;color:#9a856e;line-height:1.6}.si-matches{position:absolute;top:100%;left:0;right:0;z-index:8;box-shadow:0 12px 30px #40332122;border:1px solid #dfd2be;border-radius:11px;background:white;overflow:auto;max-height:210px}.si-matches button{display:block;width:100%;text-align:left;padding:11px 13px;background:white;border:0;border-bottom:1px solid #f0e7db;cursor:pointer}.si-matches button:hover{background:#f6eee3}.si-matches strong,.si-matches small{display:block}.si-picked{font-size:11px;color:#418557}.si-search-state{font-size:10px;color:#ab8256}.si-review{border:1px solid #e7d8c7;background:#fcf6ed;border-radius:12px;padding:19px;font-size:13px}.si-review p{font-size:12px;color:#8e7657}@media(max-width:660px){.si-grid{grid-template-columns:1fr}.si-grid .si-wide{grid-column:auto}.si-modal{padding:15px}.si-foot{align-items:flex-start;flex-direction:column}.si-primary{width:100%}.si-tabs{flex-wrap:wrap}}
.si-tiny{border:1px solid #d9c7af;background:white;color:#795c3a;padding:9px 12px;border-radius:10px;cursor:pointer;font-size:11px;font-weight:750}.si-tiny-solid{background:#795b3e;color:white}.si-supplier-box{border:1px solid #e8d8c3;background:#fcf6ec;border-radius:12px;padding:13px;display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.si-supplier-box label{display:flex;flex-direction:column;gap:6px;font-size:11px}.si-supplier-box input,.si-supplier-box select{border:1px solid #e4d2bc;border-radius:8px;padding:10px;background:white;width:100%;font-size:12px}.si-supplier-box button{align-self:end}@media(max-width:650px){.si-supplier-box{grid-template-columns:1fr}}
</style>
