const fs=require('fs');
const path=require('path');
const sharp=require(process.env.SHARP_MODULE || 'sharp');
const atlas=path.resolve(__dirname,'../..');
const previews=path.join(atlas,'预览');fs.mkdirSync(previews,{recursive:true});
(async()=>{
  for(const name of fs.readdirSync(atlas).filter(n=>/^0[0-6]·.*\.svg$/.test(n)).sort()){
    const input=path.join(atlas,name),output=input.slice(0,-4)+'.png';
    await sharp(input,{limitInputPixels:false}).png().toFile(output);
    await sharp(output).resize({width:1600}).png().toFile(path.join(previews,name.slice(0,-4)+'预览.png'));
    const info=await sharp(output).metadata();console.log(name,info.width+'×'+info.height);
  }
})().catch(e=>{console.error(e);process.exit(1)});
