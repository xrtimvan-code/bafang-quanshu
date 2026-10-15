const fs=require('fs');
const path=require('path');
const sharp=require('C:/Users/xrtim/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root='D:/dreaming/西湾盛洲志/01·图册';
(async()=>{
  for(const name of fs.readdirSync(root).filter(x=>/^0[0-3]·.*\.svg$/.test(x))){
    const target=path.join(root,name.replace(/\.svg$/,'.png'));
    await sharp(Buffer.from(fs.readFileSync(path.join(root,name)))).png().toFile(target);
    const m=await sharp(target).metadata();
    console.log(name,m.width,m.height);
  }
})();
