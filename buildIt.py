import io
import os
import imp
import json
import time
import shutil
import struct
import marshal
import zipfile
import traceback

def compileSource(source, filename = '<string>', filetime = time.time()):
	with io.BytesIO() as bytesIO:
		bytesIO.write(imp.get_magic())
		bytesIO.write(struct.pack('<I', int(filetime)))
		bytesIO.write(marshal.dumps(compile(source, filename, 'exec')))
		result = bytesIO.getvalue()
	return result

def joinPath(*args, **kwargs):
	return os.path.normpath(os.path.join(*args, **kwargs)).replace(os.sep, '/')

def sourceIterator(source_list, build_path):
	for source, build_wot, build_plugin, zip_wot, zip_plugin, is_code in sources:
		if os.path.isfile(source):
			yield (
				joinPath(source),
				joinPath(build_path, build_wot) if build_wot is not None else None,
				joinPath(build_path, build_plugin) if build_plugin is not None else None,
				joinPath(zip_wot) if zip_wot is not None else None,
				joinPath(zip_plugin) if zip_plugin is not None else None,
				is_code
			)
		elif os.path.isdir(source):
			for root, dirs, files in os.walk(source):
				root = os.path.relpath(root, source)
				for file in files:
					yield (
						joinPath(source, root, file),
						joinPath(build_path, build_wot, root, file) if build_wot is not None else None,
						joinPath(build_path, build_plugin, root, file) if build_plugin is not None else None,
						joinPath(zip_wot, root, file) if zip_wot is not None else None,
						joinPath(zip_plugin, root, file) if zip_plugin is not None else None,
						is_code
					)
	return

def processFile(src_file, dst_file_wot, dst_file_plugin, zip_file_wot, zip_file_plugin, fzip_wot, fzip_plugin, is_code=False):
	print '{0} --> {1}'.format(src_file, dst_file_wot)
	print '{0} --> {1}'.format(' ' * len(src_file), dst_file_plugin)
	if dst_file_wot is not None and not os.path.isdir(os.path.dirname(dst_file_wot)):
		os.makedirs(os.path.dirname(dst_file_wot))
	if dst_file_plugin is not None and not os.path.isdir(os.path.dirname(dst_file_plugin)):
		os.makedirs(os.path.dirname(dst_file_plugin))
	with open(src_file, 'rt' if is_code else 'rb') as f:
		source = f.read()
	source = compileSource(source, os.path.basename(src_file), os.path.getmtime(src_file)) if is_code else source
	if dst_file_wot is not None:
		with open(dst_file_wot, 'wb') as f:
			f.write(source)
	if dst_file_plugin is not None:
		with open(dst_file_plugin, 'wb') as f:
			f.write(source)
	if zip_file_wot is not None:
		fzip_wot.write(dst_file_wot, zip_file_wot)
	if zip_file_plugin is not None:
		fzip_plugin.write(dst_file_plugin, zip_file_plugin)
	return

if __name__ == '__main__':
	try:
		cfg_file = (os.path.splitext(__file__)[0] + '.cfg').replace(os.sep, '/')
		with open(cfg_file, 'rt') as f:
			config = json.load(f)
		application = config["application"]
		build_path = config["build_path"]
		release_path = config["release_path"]
		sources = config["sources"]
		if os.path.isdir(build_path):
			shutil.rmtree(build_path)
		if os.path.isdir(release_path):
			shutil.rmtree(release_path)
		os.makedirs(build_path)
		os.makedirs(release_path)
		with zipfile.ZipFile(joinPath(release_path, application + '.zip'), 'w', zipfile.ZIP_DEFLATED) as fzip_wot, zipfile.ZipFile(joinPath(release_path, application + '.sublime-package'), 'w', zipfile.ZIP_DEFLATED) as fzip_plugin:
			for src_file, dst_file_wot, dst_file_plugin, zip_file_wot, zip_file_plugin, is_code in sourceIterator(sources, build_path):
				processFile(src_file, dst_file_wot, dst_file_plugin, zip_file_wot, zip_file_plugin, fzip_wot, fzip_plugin, is_code)
	except:
		traceback.print_exc()
