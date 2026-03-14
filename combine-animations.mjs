#!/usr/bin/env node
/**
 * Headless GLB Animation Combiner
 * Combines avatar GLB with animation GLBs into a single file
 */

import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import { Group } from 'three';

const args = process.argv.slice(2);

if (args.length < 3) {
  console.error('Usage: node combine-animations.mjs <avatar.glb> <animations-dir> <output.glb>');
  process.exit(1);
}

const [avatarPath, animationsDir, outputPath] = args.map(p => resolve(p));

async function combineAnimations() {
  console.log('🎬 Starting animation combiner...');
  console.log(`📦 Avatar: ${avatarPath}`);
  console.log(`🎭 Animations: ${animationsDir}`);
  console.log(`💾 Output: ${outputPath}`);

  const gltfLoader = new GLTFLoader();
  const gltfExporter = new GLTFExporter();
  const group = new Group();

  // Load avatar
  console.log('\n📥 Loading avatar...');
  const avatarGltf = await loadGLB(gltfLoader, avatarPath);
  group.add(avatarGltf.scene);
  group.animations = [];

  // Load animations
  console.log('📥 Loading animations...');
  const { readdirSync } = await import('fs');
  const animFiles = readdirSync(animationsDir).filter(f => f.endsWith('.glb'));
  
  for (const file of animFiles) {
    const animPath = resolve(animationsDir, file);
    const animName = file.replace('.glb', '');
    
    try {
      const animGltf = await loadGLB(gltfLoader, animPath);
      if (animGltf.animations && animGltf.animations[0]) {
        animGltf.animations[0].name = animName;
        group.animations.push(animGltf.animations[0]);
        console.log(`   ✅ ${animName}`);
      }
    } catch (err) {
      console.error(`   ❌ Failed to load ${file}:`, err.message);
    }
  }

  console.log(`\n🎬 Total animations: ${group.animations.length}`);

  // Export combined GLB
  console.log('💾 Exporting combined GLB...');
  
  return new Promise((resolve, reject) => {
    gltfExporter.parse(
      avatarGltf.scene,
      (result) => {
        try {
          const buffer = Buffer.from(result);
          writeFileSync(outputPath, buffer);
          const sizeMB = (buffer.length / (1024 * 1024)).toFixed(2);
          console.log(`✅ Success! Output: ${outputPath} (${sizeMB} MB)`);
          resolve();
        } catch (err) {
          reject(err);
        }
      },
      (error) => reject(error),
      {
        binary: true,
        animations: group.animations,
        includeCustomExtensions: true
      }
    );
  });
}

function loadGLB(loader, path) {
  return new Promise((resolve, reject) => {
    const data = readFileSync(path);
    const arrayBuffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
    
    loader.parse(arrayBuffer, '', resolve, reject);
  });
}

combineAnimations()
  .then(() => {
    console.log('🎉 Done!');
    process.exit(0);
  })
  .catch((err) => {
    console.error('❌ Error:', err);
    process.exit(1);
  });
