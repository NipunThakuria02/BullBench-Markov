import {test,expect,type Page} from '@playwright/test';
// Hand-checkable UI fixtures, never production data or research results.
const metric=(brier:number)=>({n:2,events:1,base_rate:.5,brier,log_loss:.5,pr_auc:.8,balanced_accuracy:.5,macro_f1:.5});
const result={asset:'TCS',status:'development_candidate',research_track:'exploratory',model_version:'fixture-version',evaluation:{train_end:'2023-03-31',validation_start:'2023-04-04',validation_end:'2023-04-05',threshold:.01},metrics:{HMM:metric(.04),Prevalence:metric(.25)},price_metrics:{},failed_models:{},hmm_runs:[{states:2,seed:42,converged:true,trace:[-10,-8]}],calibration:'Raw probabilities; not calibrated.',caveat:'Development validation fixture only.',final_test_evaluated:false,reliability:[{model:'HMM',bin:2,n:1,mean_probability:.2,event_rate:0}],uncertainty:[]};
async function mock(page:Page,available=true){
 await page.route('**/api/results',r=>r.fulfill({json:{available:false,rows:[],reason:'No legacy evaluation'}}));
 await page.route('**/v1/**',r=>{
  const path=new URL(r.request().url()).pathname;
  if(path==='/v1/data/status')return r.fulfill({json:{assets:[{asset:'TCS',available:true,status:'imported_unverified',last_session:'2026-10-16',rows:1247}],g0_passed:false,notice:'Calendar and adjustment checks pending.'}});
  if(path==='/v1/experiments')return r.fulfill({json:{experiments:available?[{id:'tiny',asset:'TCS',status:'development_candidate'}]:[]}});
  if(path==='/v1/experiments/tiny')return r.fulfill({json:result});
  if(path.endsWith('/predictions'))return r.fulfill({status:200,contentType:'text/csv',body:'asset,origin_session,target_session,model,actual,probability\nTCS,2023-04-03,2023-04-04,HMM,0,0.2\n'});
  return r.fulfill({status:503,json:{detail:'No approved saved model bundle'}});
 });
}
test('original home and asset design expose MarkovLab beside HOME and carry the selected asset',async({page})=>{
 await mock(page);await page.goto('/');
 await expect(page.locator('.home-hero .brand')).toBeVisible();
 await expect(page.getByRole('link',{name:'MARKOVLAB',exact:true})).toBeVisible();
 await page.goto('/#/asset/hdfc-bank/models');
 await page.getByRole('link',{name:'MARKOVLAB',exact:true}).click();
 await expect(page).toHaveURL(/#\/markovlab\/hdfc-bank\/experiments$/);
 await expect(page.getByRole('heading',{name:'HDFC Bank · MarkovLab',exact:true})).toBeVisible();
 await expect(page.getByText('No saved development results for this instrument.',{exact:false})).toBeVisible();
 await page.getByRole('combobox',{name:'Search for a company'}).fill('TCS');
 await page.getByRole('combobox',{name:'Search for a company'}).press('Enter');
 await expect(page).toHaveURL(/#\/markovlab\/tcs\/experiments$/);
});
test('results show evaluation dates, baseline comparison, no final-test claim, and a verified CSV export',async({page})=>{
 await mock(page);await page.goto('/');await page.getByRole('link',{name:'MARKOVLAB',exact:true}).click();
 await expect(page.getByRole('heading',{name:'MarkovLab results'})).toBeVisible();
 await expect(page.getByText('HMM Brier score · lower is better')).toBeVisible();
 await expect(page.getByText('84.00%',{exact:true})).toBeVisible();
 await expect(page.getByText('04 Apr 2023 – 05 Apr 2023',{exact:true})).toBeVisible();
 await expect(page.getByText('Final test not run.',{exact:false})).toBeVisible();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'EXPORT VALIDATION PREDICTIONS'}).click();
 expect((await download).suggestedFilename()).toBe('tiny-validation-predictions.csv');
 await page.getByRole('link',{name:'View original TCS model comparison',exact:false}).click();
 await expect(page).toHaveURL(/#\/asset\/tcs\/models$/);
});
test('missing API outputs remain unavailable and mobile keeps the original header without overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});await mock(page,false);
 await page.goto('/#/markovlab/tcs/states');
 await expect(page.getByRole('alert')).toContainText('No approved saved model bundle');
 await page.getByLabel('State view').selectOption('smoothed');
 await expect(page.getByText('Retrospective: uses future observations',{exact:false})).toBeVisible();
 await page.getByRole('link',{name:'Risk forecasts',exact:true}).click();
 await page.getByLabel('As-of session').fill('2024-07-08');
 await page.getByRole('button',{name:'Calculate large-move probability'}).click();
 await expect(page.locator('#forecasts').getByRole('alert')).toContainText('No approved saved model bundle');
 await expect(page.locator('#forecasts').getByText('No replacement values generated.')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
});
test('malformed score payload is rejected rather than displayed',async({page})=>{
 await mock(page);
 await page.route('**/v1/experiments/tiny',r=>r.fulfill({json:{...result,metrics:{HMM:{...metric(.04),brier:'incorrect'}}}}));
 await page.goto('/#/markovlab/tcs/experiments');
 await expect(page.getByRole('alert')).toContainText('failed response validation');
 await expect(page.getByText('HMM Brier score · lower is better')).toHaveCount(0);
});

test('NIFTY zero-event results remain visible with undefined metrics clearly labelled',async({page})=>{
 await mock(page);
 await page.route('**/v1/experiments',r=>r.fulfill({json:{experiments:[{id:'index-fixture',asset:'NIFTY 50',status:'development_candidate'}]}}));
 const single={...result,asset:'NIFTY 50',metrics:{HMM:{...metric(.02),events:0,base_rate:0,pr_auc:null,balanced_accuracy:null,macro_f1:null},Prevalence:{...metric(.04),events:0,base_rate:0,pr_auc:null,balanced_accuracy:null,macro_f1:null}}};
 await page.route('**/v1/experiments/index-fixture',r=>r.fulfill({json:single}));
 await page.goto('/#/markovlab/nifty-50/experiments');
 await expect(page.getByText('Only one outcome class occurred in this validation window.',{exact:true})).toBeVisible();
 await expect(page.locator('#experiments').getByRole('cell',{name:'Not estimable',exact:true})).toHaveCount(4);
 await expect(page.getByText('HMM Brier score · lower is better')).toBeVisible();
});

test('locked historical results are labelled separately from development and prospective forecasts',async({page})=>{
 await mock(page);
 await page.route('**/v1/experiments/tiny',r=>r.fulfill({json:{...result,status:'locked_historical_test',final_test_evaluated:true,caveat:'Historical exploratory test, not untouched or prospective.',evaluation:{...result.evaluation,train_end:'2024-12-31',validation_start:'2026-01-19',validation_end:'2026-10-16'}}}));
 await page.goto('/#/markovlab/tcs/experiments');
 await expect(page.getByText('Locked historical test · exploratory',{exact:true})).toBeVisible();
 await expect(page.getByText('19 Jan 2026 – 16 Oct 2026',{exact:true})).toBeVisible();
 await expect(page.getByText('31 Dec 2024',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'EXPORT HISTORICAL TEST PREDICTIONS'})).toBeVisible();
 await expect(page.getByText('Final test not run.',{exact:false})).toHaveCount(0);
});
